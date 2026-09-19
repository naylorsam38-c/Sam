# ---- indico/modules/events/registration/controllers/display.py (whole module, symbol at 416-424) @ indico/indico@eb90264caec7 ----
# This file is part of Indico.
# Copyright (C) 2002 - 2026 CERN
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

from uuid import UUID

from flask import flash, g, jsonify, redirect, request, session
from sqlalchemy.orm import contains_eager, joinedload, lazyload, load_only, subqueryload
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from indico.core.db import db
from indico.modules.auth.util import redirect_to_login
from indico.modules.core.captcha import get_captcha_settings, invalidate_captcha
from indico.modules.events.controllers.base import RegistrationRequired, RHDisplayEventBase
from indico.modules.events.models.events import EventType
from indico.modules.events.payment import payment_event_settings
from indico.modules.events.registration import registration_settings
from indico.modules.events.registration.constants import PROFILE_PICTURE_SENTINEL
from indico.modules.events.registration.controllers import (CheckEmailMixin, RegistrationEditMixin,
                                                            RegistrationFormMixin, UploadRegistrationFileMixin,
                                                            UploadRegistrationPictureMixin)
from indico.modules.events.registration.models.form_fields import (RegistrationFormField, RegistrationFormFieldData,
                                                                   RegistrationFormItem)
from indico.modules.events.registration.models.forms import RegistrationForm
from indico.modules.events.registration.models.invitations import InvitationState, RegistrationInvitation
from indico.modules.events.registration.models.items import PersonalDataType
from indico.modules.events.registration.models.registrations import Registration, RegistrationData, RegistrationState
from indico.modules.events.registration.notifications import notify_registration_state_update
from indico.modules.events.registration.settings import event_registration_settings
from indico.modules.events.registration.util import (create_registration, generate_ticket,
                                                     get_event_regforms_registrations, get_flat_section_submission_data,
                                                     get_initial_form_values, get_user_data, load_registration_schema,
                                                     make_registration_schema)
from indico.modules.events.registration.views import (WPDisplayRegistrationFormConference,
                                                      WPDisplayRegistrationFormSimpleEvent,
                                                      WPDisplayRegistrationParticipantList)
from indico.modules.receipts.models.files import ReceiptFile
from indico.modules.users.util import SearchAffiliationsMixin, send_avatar, send_default_avatar
from indico.util.fs import secure_filename
from indico.util.i18n import _
from indico.util.marshmallow import UUIDString
from indico.web.args import use_kwargs
from indico.web.flask.util import send_file, url_for
from indico.web.util import ExpectedError


class ForbiddenPrivateRegistrationForm(Forbidden):
    """
    Indicate that access to the registration form is forbidden because
    it's private and no (valid) ``form_token`` has been provided.
    """


class RHRegistrationFormDisplayBase(RHDisplayEventBase):
    #: Whether to allow access for users who cannot access the event itself.
    ALLOW_PROTECTED_EVENT = False

    #: Whether the current request is accessing this page in restricted mode
    #: due to lack of access to the event.
    is_restricted_access = False

    @property
    def view_class(self):
        return (WPDisplayRegistrationFormConference
                if self.event.type_ == EventType.conference
                else WPDisplayRegistrationFormSimpleEvent)

    def _check_access(self):
        try:
            RHDisplayEventBase._check_access(self)
        except RegistrationRequired:
            self.is_restricted_access = True
            if not self.ALLOW_PROTECTED_EVENT or not self._check_restricted_event_access():
                raise Forbidden

    def _check_restricted_event_access(self):
        return True


class RHRegistrationFormBase(RegistrationFormMixin, RHRegistrationFormDisplayBase):
    def _process_args(self):
        RHRegistrationFormDisplayBase._process_args(self)
        RegistrationFormMixin._process_args(self)

    def _check_access(self):
        RHRegistrationFormDisplayBase._check_access(self)
        if (
            not getattr(self, 'registration', None)
            and self.regform.private
            and self.regform.uuid != request.args.get('form_token')
        ):
            raise ForbiddenPrivateRegistrationForm(_('This registration form is private.'))

    def _check_restricted_event_access(self):
        return self.regform.in_event_acls.filter_by(event_id=self.event.id).has_rows()


class RHRegistrationFormFieldActionBase(RHRegistrationFormBase):
    """Base class for a specific registration field in the public part of the registration form."""

    normalize_url_spec = {
        'locators': {
            lambda self: self.field
        },
        'skipped_args': {'section_id'}
    }

    def _process_args(self):
        RHRegistrationFormBase._process_args(self)
        self.field = (RegistrationFormField.query
                      .filter(RegistrationFormField.id == request.view_args['field_id'],
                              RegistrationFormField.registration_form == self.regform,
                              RegistrationFormField.is_enabled,
                              ~RegistrationFormField.is_deleted)
                      .one())


class RHRegistrationFormRegistrationBase(RHRegistrationFormBase):
    """Base for RHs handling individual registrations."""

    REGISTRATION_REQUIRED = True

    def _process_args(self):
        RHRegistrationFormBase._process_args(self)
        self.token = request.args.get('token')
        if self.token:
            self.registration = self.regform.get_registration(uuid=self.token)
            if not self.registration:
                raise NotFound
        else:
            self.registration = self.regform.get_registration(user=session.user) if session.user else None
        if self.REGISTRATION_REQUIRED and not self.registration:
            raise Forbidden

    def _check_access(self):
        if not self.token:
            RHRegistrationFormBase._check_access(self)


class RHRegistrationFormList(RHRegistrationFormDisplayBase):
    """List of all registration forms in the event."""

    ALLOW_PROTECTED_EVENT = True

    def _process(self):
        displayed_regforms, user_registrations = get_event_regforms_registrations(self.event, session.user,
                                                                                  only_in_acl=self.is_restricted_access)
        if len(displayed_regforms) == 1:
            return redirect(url_for('.display_regform', displayed_regforms[0]))
        multi_forms_announcement = event_registration_settings.get(self.event, 'multi_forms_announcement')
        return self.view_class.render_template('display/regform_list.html', self.event,
                                               regforms=displayed_regforms,
                                               user_registrations=user_registrations,
                                               is_restricted_access=self.is_restricted_access,
                                               description=multi_forms_announcement)


class ParticipantListRESTMixin:
    preview = None

    def is_participant(self, user):
        raise NotImplementedError

    @staticmethod
    def _is_checkin_visible(reg):
        return reg.registration_form.publish_checkin_enabled and reg.checked_in

    def _get_picture_url(self, reg, field_data):
        if not field_data or field_data.storage_file_id is None:
            return ''
        return url_for('event_registration.participant_picture', reg, field_data_id=field_data.field_data_id)

    def _merged_participant_list_table(self, is_participant):
        def _process_registration(reg, column_names):
            personal_data = reg.get_personal_data()
            columns = [{'text': personal_data.get(column_name, '')} if column_name != 'picture'
                       else {'text': self._get_picture_url(reg, reg.get_personal_data_picture()), 'is_picture': True}
                       for column_name in column_names]
            return {'id': reg.id, 'checked_in': self._is_checkin_visible(reg), 'columns': columns}

        def _deduplicate_reg_data(reg_data_iter):
            used = set()
            for reg_data in reg_data_iter:
                reg_data_hash = tuple(tuple(sorted(x.items())) for x in reg_data['columns'])
                if reg_data_hash not in used:
                    used.add(reg_data_hash)
                    yield reg_data

        column_names = registration_settings.get(self.event, 'participant_list_columns')
        headers = [PersonalDataType[column_name].get_title() for column_name in column_names]

        query = (Registration.query.with_parent(self.event)
                 .filter(Registration.is_state_publishable,
                         ~RegistrationForm.is_deleted,
                         ~RegistrationForm.participant_list_disabled)
                 .join(Registration.registration_form)
                 .options(subqueryload('data').joinedload('field_data'),
                          contains_eager('registration_form'))
                 .signal_query('merged-participant-list-publishable-registrations', event=self.event))
        num_participants = query.count()
        registrations = sorted(_deduplicate_reg_data(_process_registration(reg, column_names)
                                                     for reg in query if reg.is_publishable(is_participant)),
                               key=lambda reg: tuple(x['text'].lower() for x in reg['columns']
                                                     if not x.get('is_picture')))
        return {'headers': headers,
                'rows': registrations,
                'show_checkin': any(registration['checked_in'] for registration in registrations),
                'num_participants': num_participants,
                'num_anonymous_participants': num_participants - len(registrations)}

    def _participant_list_table(self, regform, *, is_participant):
        def _process_registration(reg, column_ids, active_fields, picture_ids):
            data_by_field = reg.data_by_field

            def _content(column_id, is_picture):
                if column_id in data_by_field:
                    if is_picture:
                        return self._get_picture_url(reg, data_by_field[column_id])
                    return data_by_field[column_id].get_friendly_data(for_humans=True)
                elif (column_id in active_fields and active_fields[column_id].personal_data_type is not None and
                        active_fields[column_id].personal_data_type.column is not None):
                    # some legacy registrations have no data in the firstname/lastname/email field
                    # so we need to get it from the registration object itself
                    return getattr(reg, active_fields[column_id].personal_data_type.column)
                else:
                    # no data available for the field
                    return ''

            def _sort_key_date(column_id):
                data = data_by_field.get(column_id)
                if data and data.field_data.field.input_type == 'date':
                    return data.data
                else:
                    return None

            columns = [{'text': _content(column_id, column_id in picture_ids), 'sort_key': _sort_key_date(column_id),
                       'is_picture': column_id in picture_ids} for column_id in column_ids]
            return {'id': reg.id, 'checked_in': self._is_checkin_visible(reg), 'columns': columns}

        active_fields = {field.id: field for field in regform.active_fields}
        picture_ids = [id for id, field in active_fields.items()
                       if field.field_impl.name == 'picture']
        column_ids = [column_id
                      for column_id in registration_settings.get_participant_list_columns(self.event, regform)
                      if column_id in active_fields]
        headers = [active_fields[column_id].title.title() for column_id in column_ids]
        query = (Registration.query.with_parent(regform)
                 .filter(Registration.is_state_publishable)
                 .options(subqueryload('data'))
                 .order_by(db.func.lower(Registration.first_name),
                           db.func.lower(Registration.last_name),
                           Registration.friendly_id)
                 .signal_query('participant-list-publishable-registrations', regform=regform))
        num_participants = query.count()
        registrations = [_process_registration(reg, column_ids, active_fields, picture_ids) for reg in query
                         if reg.is_publishable(is_participant)]

        return {'id': regform.id,
                'headers': headers,
                'rows': registrations,
                'title': regform.title,
                'show_checkin': any(registration['checked_in'] for registration in registrations),
                'num_participants': num_participants,
                'num_anonymous_participants': num_participants - len(registrations)}

    def _get_participant_list_tables(self, is_participant):
        regforms = (RegistrationForm.query.with_parent(self.event)
                    .filter(RegistrationForm.is_participant_list_visible(is_participant),
                            ~RegistrationForm.participant_list_disabled)
                    .options(subqueryload('registrations').subqueryload('data').joinedload('field_data'))
                    .signal_query('participant-list-publishable-regforms', event=self.event)
                    .all())
        if merged := bool(registration_settings.get(self.event, 'merge_registration_forms')):
            tables = [self._merged_participant_list_table(is_participant)]
        else:
            tables = []
            regforms_dict = {regform.id: regform for regform in regforms}
            for form_id in registration_settings.get_participant_list_form_ids(self.event):
                try:
                    regform = regforms_dict.pop(form_id)
                except KeyError:
                    # The settings might reference forms that are not available
                    # anymore (publishing was disabled, etc.)
                    continue
                tables.append(self._participant_list_table(regform, is_participant=is_participant))
            # There might be forms that have not been sorted by the user yet
            tables.extend(self._participant_list_table(regform, is_participant=is_participant)
                          for regform in regforms_dict.values())

        return tables, merged, regforms

    def _get_participant_list(self, is_participant):
        tables, merged, regforms = self._get_participant_list_tables(is_participant)
        num_participants = sum(table['num_participants'] for table in tables)

        return {
            'published': bool(regforms),
            'merged': merged,
            'num_participants': num_participants,
            'tables': tables,
        }

    def _process(self):
        return jsonify(self._get_participant_list(self.is_participant(session.user)))


class RHParticipantListREST(ParticipantListRESTMixin, RHRegistrationFormDisplayBase):
    """REST API for the participant list."""

    def is_participant(self, user):
        return self.event.is_user_registered(user)


class RHParticipantList(ParticipantListRESTMixin, RHRegistrationFormDisplayBase):
    """List of all public registrations."""

    view_class = WPDisplayRegistrationParticipantList  # needed for offline archive generation

    def _process(self):
        static_data = self._get_participant_list(False) if g.get('static_site') else None
        return self.view_class.render_template('display/participant_list.html', self.event, static_data=static_data)


class InvitationMixin:
    """Mixin for RHs that accept an invitation token."""

    def _process_args(self):
        self.invitation = None
        try:
            token = request.args['invitation']
        except KeyError:
            return
        try:
            UUID(hex=token)
        except ValueError:
            flash(_('Your invitation code is not valid.'), 'warning')
            return
        self.invitation = RegistrationInvitation.query.filter_by(uuid=token).with_parent(self.regform).first()
        if self.invitation is None:
            flash(_('This invitation does not exist or has been withdrawn.'), 'warning')


class RHRegistrationFormCheckEmail(CheckEmailMixin, InvitationMixin, RHRegistrationFormBase):
    """Check how an email will affect the registration."""

    ALLOW_PROTECTED_EVENT = True

    def _process_args(self):
        RHRegistrationFormBase._process_args(self)
        InvitationMixin._process_args(self)
        CheckEmailMixin._process_args(self)

    def _check_access(self):
        if not self.existing_registration and not (self.invitation and self.invitation.skip_access_check):
            try:
                RHRegistrationFormBase._check_access(self)
            except ForbiddenPrivateRegistrationForm:
                if not self.invitation:
                    raise

    def _process(self):
        return self._check_email()


class RHRegistrationForm(InvitationMixin, RHRegistrationFormRegistrationBase):
    """Display a registration form and registrations, and process submissions."""

    REGISTRATION_REQUIRED = False
    ALLOW_PROTECTED_EVENT = True

    normalize_url_spec = {
        'locators': {
            lambda self: self.regform
        }
    }

    def _check_access(self):
        try:
            RHRegistrationFormRegistrationBase._check_access(self)
        except ForbiddenPrivateRegistrationForm:
            if not self.invitation:
                raise
        except Forbidden:
            if not self.invitation or not self.invitation.skip_access_check:
                raise
            self.is_restricted_access = True
        if self.regform.require_login and not session.user and request.method != 'GET':
            raise Forbidden(response=redirect_to_login(reason=_('You are trying to register with a form '
                                                                'that requires you to be logged in')))

    def _process_args(self):
        RHRegistrationFormRegistrationBase._process_args(self)
        InvitationMixin._process_args(self)
        if self.invitation and self.invitation.state == InvitationState.accepted and self.invitation.registration:
            return redirect(url_for('.display_regform', self.invitation.registration.locator.registrant))

    @property
    def _captcha_required(self):
        """Whether a CAPTCHA should be displayed when registering."""
        return session.user is None and self.regform.require_captcha and not self.invitation

    def _can_register(self):
        if self.regform.limit_reached:
            return False
        elif self.regform.is_purged:
            return False
        elif not self.regform.is_active and self.invitation is None:
            return False
        elif session.user and self.regform.get_registration(user=session.user):
            return False
        return True

    def _process_POST(self):
        if not self._can_register():
            raise ExpectedError(_('You cannot register for this event'))

        schema_cls = make_registration_schema(self.regform, captcha_required=self._captcha_required)
        form_data = load_registration_schema(self.regform, schema_cls)
        registration = create_registration(self.regform, form_data, self.invitation)
        invalidate_captcha()
        return jsonify({'redirect': url_for('.display_regform', registration.locator.registrant)})

    def _process_GET(self):
        user_data = get_user_data(self.regform, session.user, self.invitation)
        file_data = {}

        if session.user and user_data.get('picture'):
            metadata = session.user.picture_metadata or {}
            file_data['picture'] = {
                'filename': metadata.get('filename', 'profile_picture.png'),
                'size': metadata.get('size', 0),
                'uuid': PROFILE_PICTURE_SENTINEL,
                'previewUrl': session.user.avatar_url,
            }

        initial_values = get_initial_form_values(self.regform, file_data=file_data) | user_data

        if self._captcha_required:
            initial_values |= {'captcha': None}
        return self.view_class.render_template('display/regform_display.html', self.event,
                                               regform=self.regform,
                                               form_data=get_flat_section_submission_data(self.regform),
                                               initial_values=initial_values,
                                               file_data=file_data,
                                               has_predefined_affiliations=self.regform_uses_predefined_affiliations,
                                               payment_conditions=payment_event_settings.get(self.event, 'conditions'),
                                               payment_enabled=self.event.has_feature('payment'),
                                               invitation=self.invitation,
                                               registration=self.registration,
                                               management=False,
                                               login_required=self.regform.require_login and not session.user,
                                               is_restricted_access=self.is_restricted_access,
                                               captcha_required=self._captcha_required,
                                               captcha_settings=get_captcha_settings())


class RHUploadRegistrationFile(UploadRegistrationFileMixin, InvitationMixin, RHRegistrationFormFieldActionBase):
    """Upload a file from a registration form."""

    ALLOW_PROTECTED_EVENT = True

    @use_kwargs({
        'token': UUIDString(load_default=None),
    }, location='query')
    def _process_args(self, token):
        RHRegistrationFormFieldActionBase._process_args(self)
        InvitationMixin._process_args(self)
        self.existing_registration = self.regform.get_registration(uuid=token) if token else None

    def _check_access(self):
        if not self.existing_registration:
            try:
                RHRegistrationFormFieldActionBase._check_access(self)
            except ForbiddenPrivateRegistrationForm:
                if not self.invitation:
                    raise
            except Forbidden:
                if not self.invitation or not self.invitation.skip_access_check:
                    raise


class RHUploadRegistrationPicture(UploadRegistrationPictureMixin, RHUploadRegistrationFile):
    """Upload a picture from a registration form."""


class RHSearchRegistrationAffiliation(SearchAffiliationsMixin, RHRegistrationFormFieldActionBase):
    """Search for an affiliation from a registration form."""

    @property
    def context(self):
        return {
            'event': self.event,
            'registration_form': self.regform,
            'field': self.field,
        }


class RHRegistrationDisplayEdit(RegistrationEditMixin, RHRegistrationFormRegistrationBase):
    """Submit a registration form."""

    template_file = 'display/registration_modify.html'
    management = False
    REGISTRATION_REQUIRED = False
    ALLOW_PROTECTED_EVENT = True

    def _check_access(self):
        RHRegistrationFormRegistrationBase._check_access(self)
        if not self.registration.can_be_modified:
            raise Forbidden

    def _process_args(self):
        RHRegistrationFormRegistrationBase._process_args(self)
        if self.registration is None:
            if session.user:
                flash(_('We could not find a registration for you.  If have already registered, please use the '
                        'direct access link from the email you received after registering.'), 'warning')
            else:
                flash(_('We could not find a registration for you.  If have already registered, please use the '
                        'direct access link from the email you received after registering or log in to your Indico '
                        'account.'), 'warning')
            return redirect(url_for('event_registration.display_regform', self.regform))

    @property
    def success_url(self):
        return url_for('.display_regform', self.registration.locator.registrant)


class RHRegistrationWithdraw(RHRegistrationFormRegistrationBase):
    """Withdraw a registration."""

    def _check_access(self):
        RHRegistrationFormRegistrationBase._check_access(self)
        if not self.registration.can_be_withdrawn:
            raise Forbidden

    def _process(self):
        self.registration.update_state(withdrawn=True)
        flash(_('Your registration has been withdrawn.'), 'success')
        notify_registration_state_update(self.registration)
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class RHRegistrationFormDeclineInvitation(InvitationMixin, RHRegistrationFormBase):
    """Decline an invitation to register."""

    ALLOW_PROTECTED_EVENT = True

    def _process_args(self):
        RHRegistrationFormBase._process_args(self)
        InvitationMixin._process_args(self)

    def _check_access(self):
        try:
            RHRegistrationFormBase._check_access(self)
        except ForbiddenPrivateRegistrationForm:
            pass
        except Forbidden:
            if not self.invitation.skip_access_check:
                raise
            self.is_restricted_access = True

    def _process(self):
        if self.invitation.state == InvitationState.pending:
            self.invitation.state = InvitationState.declined
            flash(_('You declined the invitation to register.'))
        if self.is_restricted_access:
            # stay on the invitation page because anything else redirects to login
            return redirect(url_for('.display_regform', self.invitation.locator.uuid))
        return redirect(self.event.url)


class RHTicketDownload(RHRegistrationFormRegistrationBase):
    """Generate ticket for a given registration."""

    def _check_access(self):
        RHRegistrationFormRegistrationBase._check_access(self)
        if self.registration.state != RegistrationState.complete:
            raise Forbidden
        if not self.regform.tickets_enabled:
            raise Forbidden
        if (not self.regform.ticket_on_event_page and not self.regform.ticket_on_summary_page
                and not self.regform.event.can_manage(session.user, 'registration')):
            raise Forbidden
        ticket_template = self.regform.get_ticket_template()
        if ticket_template.is_ticket and self.registration.is_ticket_blocked:
            raise Forbidden

    def _process(self):
        filename = secure_filename(f'{self.event.title}-Ticket.pdf', 'ticket.pdf')
        return send_file(filename, generate_ticket(self.registration), 'application/pdf')


class RHTicketGoogleWalletDownload(RHTicketDownload):
    """Redirect to the Google Wallet page for a registration ticket."""

    def _process(self):
        if not (url := self.registration.generate_ticket_google_wallet_url()):
            raise NotFound('Google Wallet tickets are not available')
        return redirect(url)


class RHTicketAppleWalletDownload(RHTicketDownload):
    """Download Apple Wallet (pkpass) registration ticket."""

    def _process(self):
        if not (apple_wallet := self.registration.generate_ticket_apple_wallet()):
            raise NotFound('Ticket for Apple Wallet is not available')
        filename = secure_filename(f'{self.event.title}-Ticket.pkpass', 'apple_wallet.pkpass')
        return send_file(filename, apple_wallet, mimetype='application/vnd.apple.pkpass', no_cache=True)


class RHRegistrationAvatar(RHDisplayEventBase):
    """Display a standard avatar for a registration based on the full name."""

    normalize_url_spec = {
        'locators': {
            lambda self: self.registration
        }
    }

    def _process_args(self):
        RHDisplayEventBase._process_args(self)
        self.registration = (Registration.query
                             .filter(Registration.id == request.view_args['registration_id'],
                                     ~Registration.is_deleted,
                                     ~RegistrationForm.is_deleted)
                             .join(Registration.registration_form)
                             .options(load_only('id', 'registration_form_id', 'is_deleted', 'first_name', 'last_name',
                                                'state', 'participant_hidden', 'consent_to_publish'),
                                      lazyload('*'),
                                      joinedload('registration_form').load_only('id', 'event_id', 'is_deleted',
                                                                                'publish_registrations_duration',
                                                                                'publish_registrations_public',
                                                                                'publish_registrations_participants'),
                                      joinedload('user').load_only('id', 'first_name', 'last_name', 'title',
                                                                   'picture_source', 'picture_metadata', 'picture'))
                             .one())

    def _check_access(self):
        RHDisplayEventBase._check_access(self)
        is_participant = self.registration.event.is_user_registered(session.user)
        if not self.registration.is_publishable(is_participant):
            raise Forbidden('Participant is not published')

    def _process(self):
        if self.registration.user:
            return send_avatar(self.registration.user)
        return send_default_avatar(self.registration.full_name)


class RHReceiptDownload(RHRegistrationFormRegistrationBase):
    """Download a receipt file from a registration."""

    normalize_url_spec = {
        'locators': {
            lambda self: self.receipt_file.locator.registrant
        },
        'copy_query_args': {'token'},
    }

    def _process_args(self):
        RHRegistrationFormRegistrationBase._process_args(self)
        self.receipt_file = (ReceiptFile.query
                             .with_parent(self.registration)
                             .filter_by(file_id=request.view_args['file_id'])
                             .first_or_404())

    def _process(self):
        return self.receipt_file.file.send()


class RHRegistrationDownloadPicture(RHRegistrationFormRegistrationBase):
    """Download a picture attached to a registration."""

    normalize_url_spec = {
        'locators': {
            lambda self: self.field_data.locator.registrant_file
        },
        'copy_query_args': {'token'},
    }

    def _process_args(self):
        RHRegistrationFormRegistrationBase._process_args(self)
        if self.registration.id != request.view_args['registration_id']:
            raise BadRequest('Invalid picture reference')
        self.field_data = (RegistrationData.query
                           .filter(RegistrationFormItem.input_type == 'picture',
                                   RegistrationData.registration_id == self.registration.id,
                                   RegistrationData.field_data_id == request.view_args['field_data_id'],
                                   RegistrationData.filename.isnot(None))
                           .join(RegistrationData.field_data)
                           .join(RegistrationFormFieldData.field)
                           .options(joinedload('registration').joinedload('registration_form'))
                           .one())

    def _process(self):
        return self.field_data.send()


class RHParticipantListPictureDownload(RHParticipantList):
    normalize_url_spec = {
        'args': {
            'field_data_id': lambda self: self.data.field_data_id
        },
        'locators': {
            lambda self: self.registration
        }
    }

    def _check_access(self):
        RHParticipantList._check_access(self)
        if registration_settings.get(self.event, 'merge_registration_forms'):
            if 'picture' not in registration_settings.get(self.event, 'participant_list_columns'):
                raise Forbidden('Picture column disabled')
            if not self.data.field_data.field.personal_data_type:
                # only main picture from personal data is in merged form
                raise Forbidden('Picture field is not the standard one')
        else:
            form = self.registration.registration_form
            participant_list_form_columns = registration_settings.get_participant_list_columns(self.event, form)
            if self.data.field_data.field_id not in participant_list_form_columns:
                raise Forbidden('Picture field is not exposed in participant list')
        is_participant = self.registration.event.is_user_registered(session.user)
        if not self.registration.is_publishable(is_participant):
            raise Forbidden('Participant is not published')

    def _process_args(self):
        RHParticipantList._process_args(self)
        self.data = (RegistrationData.query
                     .filter(RegistrationData.field_data_id == request.view_args['field_data_id'],
                             RegistrationData.registration_id == request.view_args['registration_id'],
                             RegistrationFormItem.input_type == 'picture',
                             Registration.event_id == request.view_args['event_id'],
                             Registration.registration_form_id == request.view_args['reg_form_id'],
                             ~Registration.is_deleted,
                             ~RegistrationForm.is_deleted)
                     .join(RegistrationData.field_data)
                     .join(RegistrationFormFieldData.field)
                     .join(RegistrationData.registration)
                     .join(Registration.registration_form)
                     .options(joinedload('registration').load_only(Registration.id,
                                                                   Registration.event_id,
                                                                   Registration.consent_to_publish,
                                                                   Registration.participant_hidden,
                                                                   Registration.state,
                                                                   Registration.is_deleted)
                              .joinedload('registration_form')
                              .load_only(RegistrationForm.id,
                                         RegistrationForm.event_id,
                                         RegistrationForm.publish_registrations_participants,
                                         RegistrationForm.publish_registrations_public,
                                         RegistrationForm.publish_registrations_duration),
                              lazyload('*'))
                     .one())
        self.registration = self.data.registration

    def _process(self):
        if not self.data or self.data.storage_file_id is None:
            raise NotFound('Participant has no picture')
        return self.data.send()

# ---- indico/modules/events/registration/util.py (whole module, symbol at 437-483) @ indico/indico@eb90264caec7 ----
# This file is part of Indico.
# Copyright (C) 2002 - 2026 CERN
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

import base64
import csv
import dataclasses
import itertools
import uuid
from datetime import datetime
from io import BytesIO
from operator import attrgetter

from flask import json, session
from marshmallow import RAISE, ValidationError, fields, validates
from PIL import Image, ImageOps
from qrcode import QRCode, constants
from sqlalchemy import and_, or_
from sqlalchemy.orm import contains_eager, joinedload, load_only, undefer

from indico.core import signals
from indico.core.config import config
from indico.core.db import db
from indico.core.db.sqlalchemy.util.session import no_autoflush
from indico.core.errors import UserValueError
from indico.core.marshmallow import IndicoSchema
from indico.modules.core.captcha import CaptchaField
from indico.modules.events import EventLogRealm
from indico.modules.events.models.events import Event
from indico.modules.events.models.persons import EventPerson
from indico.modules.events.payment.models.transactions import TransactionStatus
from indico.modules.events.registration import logger
from indico.modules.events.registration.constants import (PROFILE_PICTURE_SENTINEL, REGISTRATION_PICTURE_SIZE,
                                                          REGISTRATION_PICTURE_THUMBNAIL_SIZE)
from indico.modules.events.registration.fields.accompanying import AccompanyingPersonsField
from indico.modules.events.registration.fields.affiliation import AffiliationMode
from indico.modules.events.registration.fields.choices import (AccommodationField, ChoiceBaseField,
                                                               get_field_merged_options)
from indico.modules.events.registration.models.form_fields import (RegistrationFormFieldData,
                                                                   RegistrationFormPersonalDataField)
from indico.modules.events.registration.models.forms import RegistrationForm
from indico.modules.events.registration.models.invitations import InvitationState, RegistrationInvitation
from indico.modules.events.registration.models.items import (PersonalDataType, RegistrationFormItemType,
                                                             RegistrationFormPersonalDataSection)
from indico.modules.events.registration.models.registrations import (Registration, RegistrationData, RegistrationState,
                                                                     RegistrationVisibility)
from indico.modules.events.registration.notifications import (notify_invitation, notify_registration_creation,
                                                              notify_registration_modification)
from indico.modules.logs import LogKind
from indico.modules.logs.util import make_diff_log
from indico.modules.users.models.users import ProfilePictureSource
from indico.modules.users.util import get_user_by_email
from indico.util.countries import get_country_reverse
from indico.util.date_time import format_datetime, now_utc
from indico.util.i18n import _
from indico.util.signals import make_interceptable, named_objects_from_signal, values_from_signal
from indico.util.spreadsheets import CSVFieldDelimiter, csv_text_io_wrapper, unique_col
from indico.util.string import camelize_keys, validate_email, validate_email_verbose
from indico.web.args import parser


@dataclasses.dataclass
class ActionMenuEntry:
    text: str
    icon_name: str
    _: dataclasses.KW_ONLY
    weight: int = 0
    dialog_title: str = None  # defaults to `text`
    type: str = 'ajax-dialog'  # use 'callback' to call a global JS function or 'href-custom' for a data-href
    params: dict = dataclasses.field(default_factory=dict)
    url: str = ''
    callback: str = ''
    requires_selected: bool = True
    reload_page: bool = False
    hide_if_locked: bool = False
    extra_classes: str = ''


def import_user_records_from_csv(fileobj, columns, delimiter=None, *, check_email_dns=True):
    """Parse and do basic validation of user data from a CSV file.

    :param fileobj: the CSV file to be read.
    :param columns: A list of column names, 'first_name', 'last_name', & 'email' are compulsory.
    :param delimiter: the CSV separator. Guessed if omitted.
    :return: A list dictionaries each representing one row,
             the keys of which are given by the column names.
    """
    with csv_text_io_wrapper(fileobj) as ftxt:
        content = ftxt.read().splitlines()
    if not content:
        return []
    if not delimiter:
        delimiters = [d.delimiter for d in CSVFieldDelimiter]
        try:
            delimiter = csv.Sniffer().sniff('\n'.join(content[:10]), delimiters=delimiters).delimiter
        except csv.Error:
            raise UserValueError(_('Not a valid CSV file.'))
    reader = csv.reader(content, delimiter=delimiter)
    used_emails = set()
    email_row_map = {}
    user_records = []
    for row_num, row in enumerate(reader, 1):
        values = [value.strip() for value in row]
        if len(columns) != len(values):
            raise UserValueError(_('Row {}: malformed CSV data - please check that the number of columns is correct')
                                 .format(row_num))
        record = dict(zip(columns, values, strict=True))

        if not record['email']:
            raise UserValueError(_('Row {}: missing e-mail address').format(row_num))
        record['email'] = record['email'].lower()

        if not validate_email(record['email'], check_dns=check_email_dns):
            raise UserValueError(_('Row {}: invalid e-mail address').format(row_num))
        if not record['first_name'] or not record['last_name']:
            raise UserValueError(_('Row {}: missing first or last name').format(row_num))
        record['first_name'] = record['first_name'].title()
        record['last_name'] = record['last_name'].title()

        if record['email'] in used_emails:
            raise UserValueError(_('Row {}: email address is not unique').format(row_num))
        if conflict_row_num := email_row_map.get(record['email']):
            raise UserValueError(_('Row {}: email address belongs to the same user as in row {}')
                                 .format(row_num, conflict_row_num))

        used_emails.add(record['email'])
        if user := get_user_by_email(record['email']):
            email_row_map.update((e, row_num) for e in user.all_emails)

        user_records.append(record)
    return user_records


def get_title_uuid(regform, title):
    """Convert a string title to its UUID value.

    If the title does not exist in the title PD field, it will be
    ignored and returned as ``None``.
    """
    if not title:
        return None
    title_field = next((x
                        for x in regform.active_fields
                        if (x.type == RegistrationFormItemType.field_pd and
                            x.personal_data_type == PersonalDataType.title)), None)
    if title_field is None:  # should never happen
        return None
    valid_choices = {x['id'] for x in title_field.current_data.versioned_data['choices']}
    uuid = next((k for k, v in title_field.data['captions'].items() if v == title), None)
    return {uuid: 1} if uuid in valid_choices else None


def get_country_field(regform):
    """Get the country personal-data field of a regform."""
    return next((x
                 for x in regform.active_fields
                 if (x.type == RegistrationFormItemType.field_pd and
                     x.personal_data_type == PersonalDataType.country)), None)


def get_flat_section_setup_data(regform):
    section_data = {s.id: camelize_keys(s.own_data) for s in regform.sections if not s.is_deleted}
    item_data = {f.id: f.view_data for f in regform.form_items
                 if not f.is_section and not f.is_deleted and not f.parent.is_deleted}
    return {'sections': section_data, 'items': item_data}


def get_flat_section_positions_setup_data(regform):
    section_data = {s.id: s.position for s in regform.sections if not s.is_deleted}
    item_data = {f.id: f.position for f in regform.form_items
                 if not f.is_section and not f.is_deleted and not f.parent.is_deleted}
    return {'sections': section_data, 'items': item_data}


@make_interceptable
def get_flat_section_submission_data(regform, *, management=False, registration=None):
    section_data = {s.id: camelize_keys(s.own_data) for s in regform.active_sections
                    if management or not s.is_manager_only}

    item_data = {}
    registration_data = {r.field_data.field.id: r for r in registration.data} if registration else None
    for item in regform.active_fields:
        can_modify = management or not item.parent.is_manager_only
        if not can_modify:
            continue
        if registration and isinstance(item.field_impl, (ChoiceBaseField, AccommodationField)):
            field_data = get_field_merged_options(item, registration_data)
        elif registration and isinstance(item.field_impl, AccompanyingPersonsField):
            field_data = item.view_data
            field_data['availablePlaces'] = item.field_impl.get_available_places(registration)
        else:
            field_data = item.view_data
        field_data['lockedReason'] = item.get_locked_reason(registration)
        item_data[item.id] = field_data
    for item in regform.active_labels:
        if management or not item.parent.is_manager_only:
            item_data[item.id] = item.view_data
    return {'sections': section_data, 'items': item_data}


@make_interceptable
def get_initial_form_values(regform, *, management=False, **kwargs):
    """Return the initial values for registration form fields.

    This function can be intercepted by plugins, which may extend or modify
    the returned values using the provided keyword arguments.

    :param regform: The ``RegistrationForm`` whose fields are being initialized.
    :param management: If ``True``, include manager-only sections.
    :param kwargs: Additional context passed to plugin hooks.
    :returns: A dict mapping each field's ``html_field_name`` to its default
            value in camelCase format.
    """
    initial_values = {}
    for item in regform.active_fields:
        can_modify = management or not item.parent.is_manager_only
        if can_modify:
            impl = item.field_impl
            if not impl.is_invalid_field:
                initial_values[item.html_field_name] = camelize_keys(impl.ui_default_value)
    return initial_values


@make_interceptable
def get_user_data(regform: RegistrationForm, user, invitation=None):
    affiliation_field = regform.get_personal_data_field(PersonalDataType.affiliation, force=True)
    # Old regforms have a 'text' field for affiliation, new ones have a custom 'affiliation' field
    modern_affiliation_field = bool(affiliation_field and affiliation_field.input_type == 'affiliation')
    predefined_only_affiliation = (
        modern_affiliation_field and
        affiliation_field.data.get('affiliation_mode') == AffiliationMode.predefined
    )
    if user is None:
        user_data = {}
    else:
        skip = {'title', 'picture'}
        if modern_affiliation_field:
            skip.add('affiliation')
        user_data = {t.name: getattr(user, t.name, None) for t in PersonalDataType
                     if t.name not in skip and getattr(user, t.name, None)}
        if modern_affiliation_field and user.affiliation and (not predefined_only_affiliation or user.affiliation_id):
            user_data['affiliation'] = {'id': user.affiliation_id, 'text': user.affiliation or ''}
        if (
            (country_field := get_country_field(regform)) and
            country_field.data.get('use_affiliation_country') and
            user.affiliation_link and
            user.affiliation_link.country_code
        ):
            user_data['country'] = user.affiliation_link.country_code
    if invitation:
        user_data.update((attr, getattr(invitation, attr)) for attr in ('first_name', 'last_name', 'email'))
        if invitation.affiliation and (not modern_affiliation_field or not predefined_only_affiliation):
            user_data['affiliation'] = (
                {'id': None, 'text': invitation.affiliation} if modern_affiliation_field else invitation.affiliation
            )
    title = getattr(user, 'title', None)
    if title_uuid := get_title_uuid(regform, title):
        user_data['title'] = title_uuid

    active_fields = {item.personal_data_type.name for item in regform.active_fields
                     if item.type == RegistrationFormItemType.field_pd}

    if user and user.picture_source == ProfilePictureSource.custom and user.has_picture and 'picture' in active_fields:
        user_data['picture'] = PROFILE_PICTURE_SENTINEL

    return {name: value for name, value in user_data.items() if name in active_fields}


def get_form_registration_data(regform, registration, *, management=False):
    """
    Return a mapping from 'html_field_name' to the registration data.
    This also includes default values for any newly added fields since
    the React frontend requires all initial values to be present.
    """
    data_by_field = registration.data_by_field
    registration_data = {}
    for item in regform.active_fields:
        can_modify = management or not item.parent.is_manager_only
        if not can_modify:
            continue
        elif item.id in data_by_field:
            registration_data[item.html_field_name] = camelize_keys(data_by_field[item.id].user_data)
        else:
            # we never use default values when editing a registration where data does not exist yet.
            # such a field has been added after the registration has been created, and it's rather
            # confusing when you see the default value when editing your own registration, even though
            # you never set that value. and it also breaks things because when you submit the form there
            # is no value sent (since nothing changed and we send partial updates when editing), but the
            # field is required and thus validation fails
            registration_data[item.html_field_name] = item.field_impl.empty_value
    if management:
        registration_data['notify_user'] = session.get('registration_notify_user_default', True)
    return registration_data


def check_registration_email(regform, email, registration=None, management=False):
    """Check whether an email address is suitable for registration.

    :param regform: The registration form
    :param email: The email address
    :param registration: The existing registration (in case of
                         modification)
    :param management: If it's a manager adding a new registration
    """
    email = email.lower().strip()
    user = get_user_by_email(email)
    email_registration = regform.get_registration(email=email)
    user_registration = regform.get_registration(user=user) if user else None
    extra_checks = values_from_signal(
        signals.event.before_check_registration_email.send(
            regform,
            email=email, registration=registration, management=management, user=user,
            user_registration=user_registration, email_registration=email_registration),
        as_list=True)
    if extra_checks:
        return min(extra_checks, key=lambda x: ['error', 'warning', 'ok'].index(x['status']))
    if user and user != session.user and not management and not config.ALLOW_PUBLIC_USER_SEARCH:
        return {'status': 'error', 'conflict': 'email-other-user-restricted'}
    if registration is not None:
        if email_registration and email_registration != registration:
            return {'status': 'error', 'conflict': 'email-already-registered'}
        elif user_registration and user_registration != registration:
            return {'status': 'error', 'conflict': 'user-already-registered'}
        elif user and registration.user and registration.user != user:
            return {'status': 'warning' if management else 'error', 'conflict': 'email-other-user',
                    'user': user.full_name}
        elif not user and registration.user:
            return {'status': 'warning' if management else 'error', 'conflict': 'email-no-user',
                    'user': registration.user.full_name}
        elif user:
            return {'status': 'ok', 'user': user.full_name, 'self': (not management and user == session.user),
                    'same': user == registration.user}
        email_err = validate_email_verbose(email)
        if email_err:
            return {'status': 'error', 'conflict': 'email-invalid', 'email_error': email_err}
        if regform.require_user and (management or email != registration.email):
            return {'status': 'warning' if management else 'error', 'conflict': 'no-user'}
        else:
            return {'status': 'ok', 'user': None}
    else:
        if email_registration:
            return {'status': 'error', 'conflict': 'email-already-registered'}
        elif user_registration:
            return {'status': 'error', 'conflict': 'user-already-registered'}
        elif user:
            return {'status': 'ok', 'user': user.full_name, 'self': not management and user == session.user,
                    'same': False}
        email_err = validate_email_verbose(email)
        if email_err:
            return {'status': 'error', 'conflict': 'email-invalid', 'email_error': email_err}
        if regform.require_user:
            return {'status': 'warning' if management else 'error', 'conflict': 'no-user'}
        else:
            return {'status': 'ok', 'user': None}


class RegistrationSchemaBase(IndicoSchema):
    # note: this schema is kept outside `make_registration_schema` so plugins can use it in
    # subclass checks when using signals such as `schema_post_load`
    class Meta:
        unknown = RAISE


def make_registration_schema(
    regform,
    *,
    management=False,
    override_required=False,
    registration=None,
    captcha_required=False,
):
    """Dynamically create a Marshmallow schema based on the registration form fields.

    :param regform: The registration form
    :param management: True if this registration is with manager privileges
    :param override_required: True if the registration manager requested to override required fields
    :param registration: The existing registration, if it exists
    :param captcha_required: True if a captcha is present on the registration form
    """
    class RegistrationSchema(RegistrationSchemaBase):
        @validates('email')
        def validate_email(self, email, **kwargs):
            status = check_registration_email(regform, email, registration, management=management)
            if status['status'] == 'error':
                raise ValidationError('Email validation failed: ' + status['conflict'])

    schema = {}

    if management:
        schema['notify_user'] = fields.Boolean()
        schema['override_required'] = fields.Boolean()
    elif regform.needs_publish_consent:
        schema['consent_to_publish'] = fields.Enum(RegistrationVisibility)

    if captcha_required:
        schema['captcha'] = CaptchaField()

    for form_item in regform.active_fields:
        if not management and form_item.parent.is_manager_only:
            continue

        if mm_field := form_item.field_impl.create_mm_field(
            registration=registration,
            override_required=(management and override_required),
            management=management
        ):
            schema[form_item.html_field_name] = mm_field

    return RegistrationSchema.from_dict(schema, name='RegistrationSchema')


def create_personal_data_fields(regform):
    """Create the special section/fields for personal data."""
    section = next((s for s in regform.sections if s.type == RegistrationFormItemType.section_pd), None)
    if section is None:
        section = RegistrationFormPersonalDataSection(registration_form=regform, title='Personal Data')
        missing = set(PersonalDataType)
    else:
        existing = {x.personal_data_type for x in section.children if x.type == RegistrationFormItemType.field_pd}
        missing = set(PersonalDataType) - existing
    for pd_type, data in PersonalDataType.FIELD_DATA:
        if pd_type not in missing:
            continue
        field = RegistrationFormPersonalDataField(registration_form=regform, personal_data_type=pd_type,
                                                  is_required=pd_type.is_required, internal_name=pd_type.internal_name)
        for key, value in data.items():
            setattr(field, key, value)
        field.data, versioned_data = field.field_impl.process_field_data(data.pop('data', {}))
        field.current_data = RegistrationFormFieldData(versioned_data=versioned_data)
        section.children.append(field)


@no_autoflush
def create_registration(regform, data, invitation=None, management=False, notify_user=True, skip_moderation=None):
    user = session.user if session else None
    registration = Registration(registration_form=regform, user=get_user_by_email(data['email']),
                                base_price=regform.base_price, currency=regform.currency,
                                created_by_manager=management, created_by=user)
    if skip_moderation is None:
        skip_moderation = management
    all_data_by_id = {f.id: data.get(f.html_field_name) for f in regform.active_fields}
    hidden_fields = get_hidden_conditional_fields(regform, all_data_by_id)
    for form_item in regform.active_fields:
        if form_item in hidden_fields or form_item.is_purged or form_item.get_locked_reason(None):
            # Leave the registration data empty
            continue
        default = form_item.field_impl.default_value
        can_modify = management or not form_item.parent.is_manager_only
        if (invitation and invitation.lock_email and form_item.type == RegistrationFormItemType.field_pd and
                form_item.personal_data_type == PersonalDataType.email):
            value = invitation.email
        elif can_modify:
            value = data.get(form_item.html_field_name, default)
        else:
            value = default
        if value is NotImplemented:  # un-modifiable field w/ no default value
            continue
        data_entry = RegistrationData()
        registration.data.append(data_entry)
        for attr, field_value in form_item.field_impl.process_form_data(registration, value).items():
            setattr(data_entry, attr, field_value)
        if form_item.type == RegistrationFormItemType.field_pd and form_item.personal_data_type.column:
            setattr(registration, form_item.personal_data_type.column, value)
    if invitation is None:
        # Associate invitation based on email in case the user did not use the link
        invitation = (RegistrationInvitation.query
                      .filter_by(email=data['email'], registration_id=None)
                      .with_parent(regform)
                      .first())
    if invitation:
        invitation.state = InvitationState.accepted
        invitation.registration = registration
    if not management and regform.needs_publish_consent:
        registration.consent_to_publish = data.get('consent_to_publish', RegistrationVisibility.nobody)
    registration.sync_state(_skip_moderation=skip_moderation)
    db.session.flush()
    signals.event.registration_created.send(registration, management=management, data=data)
    notify_registration_creation(registration, notify_user=notify_user, from_management=management)
    logger.info('New registration %s by %s', registration, user)
    registration.log(EventLogRealm.management if management else EventLogRealm.participants,
                     LogKind.positive, 'Registration',
                     f'New registration: {registration.full_name}', user, data={'Email': registration.email})
    return registration


@no_autoflush
def modify_registration(registration, data, management=False, notify_user=True):
    from indico.modules.events.registration.tasks import delete_previous_registration_file

    user = session.user if session else None
    old_data = snapshot_registration_data(registration)
    old_price = registration.price
    personal_data_changes = {}
    regform = registration.registration_form
    data_by_field = registration.data_by_field
    if 'email' in data and (management or not registration.user):
        registration.user = get_user_by_email(data['email'])

    billable_items_locked = not management and registration.is_paid
    active_fields = regform.active_fields

    # Get both the existing data and the new data from the client as modifying registrations
    # sends a PATCH with only updated fields in the payload.
    all_data_by_id = {field_id: field_data.data for field_id, field_data in data_by_field.items()}
    all_data_by_id.update({f.id: data[f.html_field_name] for f in regform.active_fields if f.html_field_name in data})
    hidden_fields = get_hidden_conditional_fields(regform, all_data_by_id)

    def _set_data(field, value):
        attrs = field.field_impl.process_form_data(registration, value, data_by_field[field.id],
                                                   billable_items_locked=billable_items_locked)
        for key, val in attrs.items():
            setattr(data_by_field[field.id], key, val)
        if field.type == RegistrationFormItemType.field_pd and field.personal_data_type.column:
            key = field.personal_data_type.column
            if getattr(registration, key) != value:
                personal_data_changes[key] = value
            setattr(registration, key, value)

    for form_item in active_fields:
        if form_item.is_purged or form_item.get_locked_reason(registration):
            continue

        field_impl = form_item.field_impl
        has_data = form_item.html_field_name in data
        can_modify = management or not form_item.parent.is_manager_only
        existing_data = data_by_field.get(form_item.id)

        if form_item in hidden_fields:
            if not existing_data:
                continue
            if field_impl.is_file_field and existing_data and existing_data.storage_file_id is not None:
                delete_previous_registration_file.apply_async([existing_data.registration_id,
                                                               existing_data.field_data_id,
                                                               existing_data.storage_backend,
                                                               existing_data.storage_file_id], countdown=600)
            registration.data.remove(existing_data)
            continue

        if has_data and can_modify:
            value = data.get(form_item.html_field_name)
        elif not has_data and form_item.id not in data_by_field and not management:
            # set default value for a field if it didn't have one before (including manager-only fields).
            # but we do so only if it's the user editing their registration - if a manager edits
            # the registration, we keep those fields empty so it's clear they have never been
            # filled in.
            value = field_impl.default_value
        else:
            # keep current value
            continue

        if value is NotImplemented:  # un-modifiable field w/ no existing nor default value
            continue

        if field_impl.is_file_field and existing_data and existing_data.storage_file_id is not None:
            delete_previous_registration_file.apply_async([existing_data.registration_id,
                                                           existing_data.field_data_id,
                                                           existing_data.storage_backend,
                                                           existing_data.storage_file_id], countdown=600)
        if form_item.id not in data_by_field:
            data_by_field[form_item.id] = RegistrationData(registration=registration,
                                                           field_data=form_item.current_data)
        _set_data(form_item, value)

    if not management and regform.needs_publish_consent:
        consent_to_publish = data.get('consent_to_publish')
        if consent_to_publish is not None:
            update_registration_consent_to_publish(registration, consent_to_publish)

    registration.sync_state(_skip_moderation=management)
    registration.set_modified()
    db.session.flush()
    # sanity check
    if billable_items_locked and old_price != registration.price:
        raise Exception('There was an error while modifying your registration (price mismatch: %s / %s)',
                        old_price, registration.price)
    if personal_data_changes:
        signals.event.registration_personal_data_modified.send(registration, change=personal_data_changes)
    signals.event.registration_updated.send(registration, management=management, data=data)

    new_data = snapshot_registration_data(registration)
    diff = diff_registration_data(old_data, new_data)
    notify_registration_modification(registration, notify_user=notify_user, diff=diff, old_price=old_price,
                                     from_management=management)
    logger.info('Registration %s modified by %s', registration, user)
    registration.log(EventLogRealm.management if management else EventLogRealm.participants,
                     LogKind.change, 'Registration',
                     f'Registration modified: {registration.full_name}',
                     user, data={'Email': registration.email})


def update_registration_consent_to_publish(registration, consent_to_publish):
    if registration.consent_to_publish == consent_to_publish:
        return
    changes = make_diff_log({'consent_to_publish': (registration.consent_to_publish, consent_to_publish)},
                            {'consent_to_publish': 'Consent to publish'})
    registration.log(EventLogRealm.participants, LogKind.change, 'Registration',
                     f'Consent to publish modified: {registration.full_name}',
                     session.user, data={'Email': registration.email, 'Changes': changes})
    registration.consent_to_publish = consent_to_publish


def get_registration_spreadsheet_column_formats(regform_items):
    """Return the configured formats for date columns in registration exports."""
    return {
        unique_col(item.title, item.id): item.data['date_format']
        for item in regform_items if item.input_type == 'date'
    }


def generate_spreadsheet_from_registrations(registrations, regform_items, static_items, extra_columns=()):
    """Generate a spreadsheet data from a given registration list.

    :param registrations: The list of registrations to include in the file
    :param regform_items: The registration form items to be used as columns
    :param static_items: Registration form information as extra columns
    :param extra_columns: Custom list items from the `registrant_list_items` signal
    """
    field_names = ['ID', 'Name']
    special_item_mapping = {
        'reg_date': ('Registration date', lambda x: x.submitted_dt),
        'mod_date': ('Modification date', lambda x: x.modified_dt),
        'state': ('Registration state', lambda x: x.state.title),
        'created_by': ('Created by', lambda x: x.created_by.full_name if x.created_by else ''),
        'price': ('Price', lambda x: x.render_price()),
        'checked_in': ('Checked in', lambda x: x.checked_in),
        'checked_in_date': ('Check-in date', lambda x: x.checked_in_dt if x.checked_in else ''),
        'payment_date': ('Payment date', lambda x: (x.transaction.timestamp
                                                    if (x.transaction is not None and
                                                        x.transaction.status == TransactionStatus.successful)
                                                    else '')),
        'tags_present': ('Tags', lambda x: [t.title for t in x.tags] if x.tags else ''),
    }
    for item in regform_items:
        field_names.append(unique_col(item.title, item.id))
        if item.input_type == 'accommodation':
            field_names.append(unique_col('{} ({})'.format(item.title, 'Arrival'), item.id))
            field_names.append(unique_col('{} ({})'.format(item.title, 'Departure'), item.id))
    field_names.extend(title for name, (title, fn) in special_item_mapping.items() if name in static_items)
    field_names.extend(str(col.title) for col in extra_columns)
    rows = []
    for registration in registrations:
        data = registration.data_by_field
        registration_dict = {
            'ID': registration.friendly_id,
            'Name': f'{registration.first_name} {registration.last_name}'
        }
        tzinfo = registration.event.tzinfo
        for item in regform_items:
            key = unique_col(item.title, item.id)
            if item.input_type == 'accommodation':
                registration_dict[key] = data[item.id].friendly_data.get('choice') if item.id in data else ''
                key = unique_col('{} ({})'.format(item.title, 'Arrival'), item.id)
                arrival_date = data[item.id].friendly_data.get('arrival_date') if item.id in data else None
                registration_dict[key] = arrival_date or ''
                key = unique_col('{} ({})'.format(item.title, 'Departure'), item.id)
                departure_date = data[item.id].friendly_data.get('departure_date') if item.id in data else None
                registration_dict[key] = departure_date or ''
            elif item.input_type == 'date':
                if item.id not in data or not data[item.id].data:  # missing or empty data for the field
                    registration_dict[key] = ''
                    continue
                registration_dict[key] = datetime.fromisoformat(data[item.id].data).replace(tzinfo=tzinfo)
            elif item.id in data:
                registration_dict[key] = item.field_impl.render_spreadsheet_data(data[item.id])
            else:
                registration_dict[key] = ''
        for name, (title, fn) in special_item_mapping.items():
            if name not in static_items:
                continue
            value = fn(registration)
            registration_dict[title] = value
        for col in extra_columns:
            col_data = col.data.get(registration)
            registration_dict[str(col.title)] = col_data.text_value if col_data else ''
        rows.append(registration_dict)
    return field_names, rows


def generate_pdf_data_from_registrations(event, registrations, regform_items, static_items, extra_columns, empty_value):
    """Generate data for PDF creation for a given registration list.

    :param event: The event containing the registrations
    :param registrations: The list of registrations to include
    :param regform_items: The registration form items to be used as columns
    :param static_items: Registration form information as extra columns
    :param extra_columns: Custom list items from the `registrant_list_items` signal
    :param empty_value: Value to use when no data is available
    """
    field_names = [_('ID'), _('Name')]
    special_item_mapping = {
        'reg_date': (
            _('Registration date'),
            lambda x: format_datetime(x.submitted_dt, timezone=event.tzinfo),
        ),
        'mod_date': (
            _('Modification date'),
            lambda x: format_datetime(x.submitted_dt, timezone=event.tzinfo) if x.submitted_dt else empty_value,
        ),
        'state': (
            _('Registration state'),
            lambda x: x.state.title,
        ),
        'created_by': (
            _('Created by'),
            lambda x: x.created_by.full_name if x.created_by else empty_value,
        ),
        'price': (
            _('Price'),
            lambda x: x.render_price(),
        ),
        'checked_in': (
            _('Checked in'),
            lambda x: x.checked_in,
        ),
        'checked_in_date': (
            _('Check-in date'),
            lambda x: format_datetime(x.checked_in_dt, timezone=event.tzinfo) if x.checked_in else '',
        ),
        'payment_date': (
            _('Payment date'),
            lambda x: (
                format_datetime(x.transaction.timestamp, timezone=event.tzinfo)
                if (x.transaction is not None and x.transaction.status == TransactionStatus.successful)
                else ''
            ),
        ),
        'tags_present': (
            _('Tags'),
            lambda x: [t.title for t in x.tags] if x.tags else '',
        ),
    }
    field_names.extend(unique_col(item.title, item.id) for item in regform_items)
    field_names.extend(title for name, (title, fn) in special_item_mapping.items() if name in static_items)
    field_names.extend(str(col.title) for col in extra_columns)
    rows = []
    for registration in registrations:
        data = registration.data_by_field
        row_data = {
            _('ID'): f'#{registration.friendly_id}',
            _('Name'): f'{registration.first_name} {registration.last_name}'
        }
        for item in regform_items:
            key = unique_col(item.title, item.id)
            if item.id not in data:
                row_data[key] = empty_value
            else:
                col = item.field_impl.render_reglist_column(data[item.id])
                if item.input_type == 'accommodation':
                    # XXX ugly hack, but the "content" for this field is a dict...
                    row_data[key] = col.text_value
                else:
                    row_data[key] = col.content
        for name, (title, fn) in special_item_mapping.items():
            if name not in static_items:
                continue
            value = fn(registration)
            row_data[title] = value
        for col in extra_columns:
            col_data = col.data.get(registration)
            row_data[str(col.title)] = col_data.text_value if col_data else empty_value
        rows.append((registration, row_data))
    return field_names, rows


def get_registrations_with_tickets(user, event):
    query = (Registration.query.with_parent(event)
             .filter(Registration.user == user,
                     Registration.state == RegistrationState.complete,
                     RegistrationForm.tickets_enabled,
                     RegistrationForm.ticket_on_event_page,
                     ~RegistrationForm.is_deleted,
                     ~Registration.is_deleted)
             .join(Registration.registration_form))

    cached_templates = {}

    def _is_ticket_blocked(registration):
        regform = registration.registration_form
        if regform not in cached_templates:
            cached_templates[regform] = regform.get_ticket_template()
        return cached_templates[regform].is_ticket and registration.is_ticket_blocked

    return [r for r in query if not _is_ticket_blocked(r)]


def get_published_registrations(event, is_participant):
    """Get a list of published registrations for an event.

    :param event: the `Event` to get registrations for
    :param is_participant: whether the user accessing the registrations is a participant of the event
    :return: list of `Registration` objects
    """
    query = (Registration.query.with_parent(event)
             .filter(Registration.is_publishable(is_participant),
                     ~RegistrationForm.is_deleted,
                     ~Registration.is_deleted)
             .join(Registration.registration_form)
             .options(contains_eager(Registration.registration_form))
             .order_by(db.func.lower(Registration.first_name),
                       db.func.lower(Registration.last_name),
                       Registration.friendly_id))

    return query.all()


def count_hidden_registrations(event, is_participant):
    """Get the number of hidden registrations for an event.

    :param event: the `Event` to get registrations for
    :param is_participant: whether the user accessing the registrations is a participant of the event
    :return: number of registrations
    """
    query = (Registration.query.with_parent(event)
             .filter(Registration.is_state_publishable,
                     ~Registration.is_publishable(is_participant),
                     RegistrationForm.is_participant_list_visible(is_participant))
             .join(Registration.registration_form))

    return query.count()


def get_events_registered(user, dt=None):
    """Get the IDs of events where the user is registered.

    :param user: A `User`
    :param dt: Only include events taking place on/after that date
    :return: A set of event ids
    """
    query = (user.registrations
             .options(load_only('event_id'))
             .options(joinedload(Registration.registration_form).load_only('event_id'))
             .join(Registration.registration_form)
             .join(RegistrationForm.event)
             .filter(Registration.is_active, ~RegistrationForm.is_deleted, ~Event.is_deleted,
                     Event.ends_after(dt)))
    return {registration.event_id for registration in query}


def build_registrations_api_data(event):
    api_data = []
    query = (RegistrationForm.query.with_parent(event)
             .options(joinedload('registrations').joinedload('data').joinedload('field_data')))
    for regform in query:
        for registration in regform.active_registrations:
            registration_info = _build_base_registration_info(registration)
            registration_info['checkin_secret'] = registration.ticket_uuid
            api_data.append(registration_info)
    return api_data


def _build_base_registration_info(registration):
    personal_data = _build_personal_data(registration)
    return {
        'registrant_id': str(registration.id),
        'checked_in': registration.checked_in,
        'checkin_secret': registration.ticket_uuid,
        'full_name': '{} {}'.format(personal_data.get('title', ''), registration.full_name).strip(),
        'personal_data': personal_data,
        'tags': sorted(t.title for t in registration.tags),
    }


def _build_personal_data(registration):
    personal_data = registration.get_personal_data()
    personal_data['firstName'] = personal_data.pop('first_name')
    personal_data['surname'] = personal_data.pop('last_name')
    personal_data['country'] = personal_data.pop('country', '')
    personal_data['country_code'] = get_country_reverse(personal_data['country']) or ''
    personal_data['phone'] = personal_data.pop('phone', '')
    return personal_data


def build_registration_api_data(registration):
    registration_info = _build_base_registration_info(registration)
    registration_info['amount_paid'] = registration.price if registration.is_paid else 0
    registration_info['ticket_price'] = registration.price
    registration_info['registration_date'] = registration.submitted_dt.isoformat()
    registration_info['paid'] = registration.is_paid
    registration_info['checkin_date'] = registration.checked_in_dt.isoformat() if registration.checked_in_dt else ''
    registration_info['event_id'] = registration.event_id
    return registration_info


def get_ticket_qr_code_data(person):
    """Get the data which will be saved in a ticket QR code.

    QR code format:

    {
        'i': [qr_code_version, indico_url, b64(checkin_secret), b64(person_id)],
        # extra keys may be added by plugins (e.g. site access)
    }

    This format tries to be as compact as possible so that the resulting QR codes
    are small and easy to scan. However, we need to stick with a JSON dictionary in
    order to be compatible with the site access plugin which inserts an extra key
    with the ADaMS URL.

    Note that `person_id` is only included if this is a ticket for an accompanying person.

    The checkin secret and person id (if present) is base64-encoded to save space
    (see https://stackoverflow.com/a/53136913/3911147).

    If Indico is running on HTTPS, the scheme ('https://') is stripped from the
    URL to save a few extra bytes.
    """
    registration = person['registration']
    is_accompanying = person['is_accompanying']
    person_id = person['id']
    checkin_secret = person['registration'].ticket_uuid

    qr_code_version = 2  # Increment this if the QR code format changes
    url = config.BASE_URL.removeprefix('https://')

    data = {
        'i': [qr_code_version, url, _base64_encode_uuid(checkin_secret)]
    }
    if is_accompanying:
        data['i'].append(_base64_encode_uuid(person_id))

    sig_rvs = values_from_signal(signals.event.registration.generate_ticket_qr_code.send(registration, person=person,
                                                                                         ticket_data=data),
                                 as_list=True)
    if not sig_rvs:
        return data
    elif len(sig_rvs) == 1:
        return sig_rvs[0]
    else:
        raise RuntimeError('Multiple values returned by `generate_ticket_qr_code` signal')


def _base64_encode_uuid(uid):
    return base64.b64encode(uuid.UUID(uid).bytes).decode('ascii')


def generate_ticket_qr_code(person):
    """Generate an image with a QR code encoding a check-in ticket.

    :param registration: corresponding `Registration` object
    :return: A `BytesIO` containing the image data
    """
    qr = QRCode(
        version=None,
        error_correction=constants.ERROR_CORRECT_M,
        box_size=3,
        border=1
    )
    data = get_ticket_qr_code_data(person)
    qr_data = json.dumps(data, separators=(',', ':')) if not isinstance(data, str) else data
    qr.add_data(qr_data)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image().save(buf)
    buf.seek(0)
    return buf


def get_event_regforms(event, user, with_registrations=False, only_in_acl=False):
    """Get registration forms with information about user registrations.

    :param event: the `Event` to get registration forms for
    :param user: A `User`
    :param with_registrations: Whether to return the user's
                               registration instead of just
                               whether they have one
    :param only_in_acl: Whether to include only registration forms
                        that are in the event's ACL
    """
    if not user:
        registered_user = db.literal(None if with_registrations else False)
    elif with_registrations:
        registered_user = Registration
    else:
        registered_user = RegistrationForm.registrations.any((Registration.user == user) & ~Registration.is_deleted)
    query = (RegistrationForm.query.with_parent(event)
             .with_entities(RegistrationForm, registered_user)
             .options(undefer('active_registration_count'))
             .order_by(db.func.lower(RegistrationForm.title)))
    if only_in_acl:
        query = query.filter(RegistrationForm.in_event_acls.any(event=event))
    if with_registrations:
        user_criterion = (Registration.user == user) if user else False
        query = query.outerjoin(Registration, db.and_(Registration.registration_form_id == RegistrationForm.id,
                                                      user_criterion,
                                                      ~Registration.is_deleted))
    return query.all()


def get_event_regforms_registrations(event, user, include_scheduled=True, only_in_acl=False):
    """Get regforms and the associated registrations for an event+user.

    :param event: the `Event` to get registration forms for
    :param user: A `User`
    :param include_scheduled: Whether to include scheduled
                              but not open registration forms
    :param only_in_acl: Whether to include only registration forms
                        that are in the event's ACL
    :return: A tuple, which includes:
            - All registration forms which are scheduled, open or registered.
            - A dict mapping all registration forms to the user's registration if they have one.
    """
    all_regforms = get_event_regforms(event, user, with_registrations=True, only_in_acl=only_in_acl)
    if include_scheduled:
        displayed_regforms = [regform for regform, registration in all_regforms
                              if (regform.is_scheduled and not regform.private) or registration]
    else:
        displayed_regforms = [regform for regform, registration in all_regforms
                              if (regform.is_open and not regform.private) or registration]
    return displayed_regforms, dict(all_regforms)


def generate_ticket(registration):
    from indico.modules.events.registration.badges import RegistrantsListToBadgesPDF, RegistrantsListToBadgesPDFFoldable
    from indico.modules.events.registration.controllers.management.tickets import DEFAULT_TICKET_PRINTING_SETTINGS
    template = registration.registration_form.get_ticket_template()
    registrations = [registration]
    signals.event.designer.print_badge_template.send(template, regform=registration.registration_form,
                                                     registrations=registrations)
    pdf_class = RegistrantsListToBadgesPDFFoldable if template.backside_template else RegistrantsListToBadgesPDF
    pdf = pdf_class(template, DEFAULT_TICKET_PRINTING_SETTINGS, registration.event, registrations,
                    registration.registration_form.tickets_for_accompanying_persons)
    return pdf.get_pdf()


def get_ticket_attachments(registration):
    return [('Ticket.pdf', generate_ticket(registration).getvalue())]


def update_regform_item_positions(regform):
    """Update positions when deleting/disabling an item in order to prevent gaps."""
    section_positions = itertools.count(1)
    disabled_section_positions = itertools.count(1000)
    for section in sorted(regform.sections, key=attrgetter('position')):
        section_active = section.is_enabled and not section.is_deleted
        section.position = next(section_positions if section_active else disabled_section_positions)
        # ensure consistent field ordering
        positions = itertools.count(1)
        disabled_positions = itertools.count(1000)
        for child in section.children:
            child_active = child.is_enabled and not child.is_deleted
            child.position = next(positions if child_active else disabled_positions)


def create_invitation(regform, user, email_sender, email_subject, email_body, *, skip_moderation, skip_access_check,
                      lock_email, bcc_addresses=None, copy_for_sender=False):
    invitation = RegistrationInvitation(
        email=user['email'],
        first_name=user['first_name'],
        last_name=user['last_name'],
        affiliation=user['affiliation'],
        skip_moderation=skip_moderation,
        skip_access_check=skip_access_check,
        lock_email=lock_email,
    )
    regform.invitations.append(invitation)
    db.session.flush()
    notify_invitation(invitation, email_subject, email_body, email_sender,
                      bcc_addresses=bcc_addresses, copy_for_sender=copy_for_sender)
    return invitation


def import_registrations_from_csv(regform, fileobj, skip_moderation=True, notify_users=False, delimiter=','):
    """Import event registrants from a CSV file into a form."""
    columns = ['first_name', 'last_name', 'affiliation', 'position', 'phone', 'email']
    user_records = import_user_records_from_csv(fileobj, columns=columns, delimiter=delimiter)

    reg_data = (db.session.query(Registration.user_id, Registration.email)
                .with_parent(regform)
                .filter(Registration.is_active)
                .all())
    registered_user_ids = {rd.user_id for rd in reg_data if rd.user_id is not None}
    registered_emails = {rd.email for rd in reg_data}

    for row_num, record in enumerate(user_records, 1):
        if record['email'] in registered_emails:
            raise UserValueError(_('Row {}: a registration with this email already exists').format(row_num))

        user = get_user_by_email(record['email'])
        if user and user.id in registered_user_ids:
            raise UserValueError(_('Row {}: a registration for this user already exists').format(row_num))

    return [
        create_registration(regform, data, management=True, notify_user=notify_users, skip_moderation=skip_moderation)
        for data in user_records
    ]


def import_invitations_from_user_records(regform, user_records, email_sender, email_subject, email_body, *,
                                         skip_moderation=True, skip_access_check=True, skip_existing=False,
                                         lock_email=False, bcc_addresses=None, copy_for_sender=False):
    """Import invitations from a user records list.

    :return: A list of invitations and the number of skipped records which
             is zero if skip_existing=False
    """
    reg_data = (db.session.query(Registration.user_id, Registration.email)
                .with_parent(regform)
                .filter(Registration.is_active)
                .all())
    registered_user_ids = {rd.user_id for rd in reg_data if rd.user_id is not None}
    registered_emails = {rd.email for rd in reg_data}
    invited_emails = {inv.email for inv in regform.invitations}

    filtered_records = []
    for row_num, user in enumerate(user_records, 1):
        if user['email'] in registered_emails:
            if skip_existing:
                continue
            raise UserValueError(_('Row {}: a registration with this email already exists').format(row_num))

        indico_user = get_user_by_email(user['email'])
        if indico_user and indico_user.id in registered_user_ids:
            if skip_existing:
                continue
            raise UserValueError(_('Row {}: a registration for this user already exists').format(row_num))

        if user['email'] in invited_emails:
            if skip_existing:
                continue
            raise UserValueError(_('Row {}: an invitation for this user already exists').format(row_num))

        filtered_records.append(user)

    invitations = [create_invitation(regform, user, email_sender, email_subject, email_body,
                                     skip_moderation=skip_moderation, skip_access_check=skip_access_check,
                                     lock_email=lock_email, bcc_addresses=bcc_addresses,
                                     copy_for_sender=copy_for_sender)
                   for user in filtered_records]
    skipped_records = len(user_records) - len(filtered_records)
    return invitations, skipped_records


def get_registered_event_persons(event):
    """Get all registered EventPersons of an event."""
    query = (event.persons
             .join(Registration, and_(Registration.event_id == EventPerson.event_id,
                                      Registration.is_active,
                                      or_(Registration.user_id == EventPerson.user_id,
                                          Registration.email == EventPerson.email)))
             .join(RegistrationForm, and_(RegistrationForm.id == Registration.registration_form_id,
                                          ~RegistrationForm.is_deleted)))
    return set(query)


def serialize_registration_form(regform):
    """Serialize registration form to JSON-like object."""
    return {
        'id': regform.id,
        'name': regform.title,
        'identifier': f'RegistrationForm:{regform.id}',
        '_type': 'RegistrationForm'
    }


def snapshot_registration_data(registration):
    data = {}
    for regfields in registration.get_summary_data().values():
        for field, regdata in regfields.items():
            data[field.html_field_name] = {'price': regdata.price, 'data': regdata.data,
                                           'storage_file_id': regdata.storage_file_id,
                                           'is_file_field': field.field_impl.is_file_field,
                                           'friendly_data': field.field_impl.get_snapshot_data(regdata)}
    return data


def diff_registration_data(old_data, new_data):
    """Compare two sets of registration data.

    :return: A dictionary where the key is the html name of the field and the value is
             the old and new friendly data and the field price
    """
    diff = {}
    for html_field_name in old_data.keys() | new_data.keys():
        old = old_data.get(html_field_name)
        new = new_data.get(html_field_name)
        if old is None:
            diff[html_field_name] = {
                'old': {'price': 0, 'friendly_data': ''},
                'new': {'price': new['price'], 'friendly_data': new['friendly_data']}
            }
        elif new is None:
            # XXX this doesn't actually get displayed in the emails
            diff[html_field_name] = {
                'old': {'price': old['price'], 'friendly_data': old['friendly_data']},
                'new': {'price': 0, 'friendly_data': ''}
            }
        elif old['data'] != new['data'] or (old['is_file_field'] and old['storage_file_id'] != new['storage_file_id']):
            diff[html_field_name] = {
                'old': {'price': old['price'], 'friendly_data': old['friendly_data']},
                'new': {'price': new['price'], 'friendly_data': new['friendly_data']}
            }
    return diff


def close_registration(regform):
    regform.end_dt = now_utc()
    if not regform.has_started:
        regform.start_dt = regform.end_dt


def clone_registration_form(regform: RegistrationForm, title: str) -> RegistrationForm:
    """Clone a registration form within the same event.

    :param regform: The registration form to clone
    :param title: The title for the new registration form
    :return: The cloned registration form
    """
    from indico.modules.events.registration.clone import RegistrationFormCloner
    return RegistrationFormCloner.clone_single_regform(regform, title=title)


def get_persons(registrations, include_accompanying_persons=False):
    persons = []
    for registration in registrations:
        persons.append({
            'id': registration.id,
            'first_name': registration.first_name,
            'last_name': registration.last_name,
            'registration': registration,
            'is_accompanying': False,
        })
        if include_accompanying_persons:
            persons.extend({'id': person['id'],
                            'first_name': person['firstName'],
                            'last_name': person['lastName'],
                            'registration': registration,
                            'is_accompanying': True} for person in registration.accompanying_persons)
    return persons


@make_interceptable
def process_registration_picture(source, *, thumbnail=False, target_format='JPEG'):
    """Resize the picture to a maximum size and save it in the target format."""
    max_size = REGISTRATION_PICTURE_THUMBNAIL_SIZE if thumbnail else REGISTRATION_PICTURE_SIZE
    try:
        picture = Image.open(source)
    except (OSError, Image.DecompressionBombError):
        return None
    picture = ImageOps.exif_transpose(picture)
    if target_format == 'JPEG' and picture.mode != 'RGB':
        picture = picture.convert('RGB')
    size_x, size_y = picture.size
    if max(size_x, size_y) > max_size:
        ratio = max_size / max(size_x, size_y)
        picture = picture.resize((max(1, int(ratio * size_x)), max(1, int(ratio * size_y))), Image.Resampling.BICUBIC)
    image_bytes = BytesIO()
    picture.save(image_bytes, target_format)
    image_bytes.seek(0)
    return image_bytes


def is_conditional_field_shown(field, data, *, is_db_data=False):
    # not conditional
    if not field.show_if_field:
        return True
    # condition field has no data
    if (show_if_data := data.get(field.show_if_id)) is None:
        return False
    if is_db_data:
        show_if_data = show_if_data.data
        if show_if_data is None:
            return False
    current_values = field.show_if_field.field_impl.get_data_for_condition(show_if_data)
    condition_values = set(field.show_if_values)
    if not (current_values & condition_values):
        return False
    # recurse to the condition field in case it's also conditional
    return is_conditional_field_shown(field.show_if_field, data, is_db_data=is_db_data)


@make_interceptable
def get_hidden_conditional_fields(regform, data_by_id):
    return {f for f in regform.active_fields if not is_conditional_field_shown(f, data_by_id)}


def load_registration_schema(regform, schema_cls, *, registration=None, partial_fields=frozenset()):
    """Process data using the registration schema.

    This takes conditional fields into account so required fields which
    are disabled due to a condition do not cause a validation error, but
    required fields that are active are actually enforced as required.
    """
    # During the first parse all fields may be omitted; we could limit this to conditional
    # fields but it doesn't really matter as we just need to get field values.
    schema = schema_cls(partial=True)
    all_form_data = parser.parse(schema)
    if registration:
        # Use existing data from the registration, and then extend/overwrite it with new data
        data_by_id = {field_id: field_data.data for field_id, field_data in registration.data_by_field.items()}
        data_by_id.update({f.id: all_form_data[f.html_field_name] for f in regform.active_fields
                           if f.html_field_name in all_form_data})
    else:
        data_by_id = {f.id: all_form_data.get(f.html_field_name) for f in regform.active_fields}
    hidden_fields = get_hidden_conditional_fields(regform, data_by_id)
    # Now that we know which fields are disabled due to unmet conditions, we can parse
    # the form data again and properly fail if any required fields are missing/empty.
    # XXX: The frontend is not supposed to send data for any field that is disabled,
    #      so we can use `exclude` here even with `unknown=RAISE` on the schema.
    schema = schema_cls(partial=partial_fields, exclude={f.html_field_name for f in hidden_fields})
    return parser.parse(schema)


def get_custom_ticket_qr_code_handlers():
    """Get a dict containing custom ticket QR code handlers."""
    return named_objects_from_signal(signals.event.registration.custom_ticket_qr_code_handler.send())


class CustomTicketCode:
    """Base class for custom ticket codes."""

    #: unique name of the code - must be all-lowercase
    name = None
    #: Regex used by the checkin app to match all ticket codes that should be handled by this class.
    #: This regex will be used in JavaScript code, so make sure to not use anything Python-specific.
    regex = None

    @classmethod
    def lookup_registration(cls, data: str) -> Registration | None:
        """Lookup a registration based on custom ticket code data."""
        raise NotImplementedError
