# Attach Points

Application: adamspd/django-appointment
Repository: adamspd/django-appointment
Commit: 
Framework: django
Datastore: 

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| appointment.Service | Service | READ, WRITE | name, description, duration, price, down_payment, image, currency, background_color, reschedule_limit, allow_rescheduling, use_service_duration_as_slot, created_at, updated_at | appointment/models.py:64, appointment/forms.py (write path) |
| appointment.StaffMember | StaffMember | READ, WRITE | user, services_offered, slot_duration, lead_time, finish_time, appointment_buffer_time, slot_gap_time, work_on_saturday, work_on_sunday, created_at, updated_at | appointment/models.py:230, appointment/services.py (write path) |
| appointment.AppointmentRequest | AppointmentRequest | READ, WRITE | date, start_time, end_time, service, staff_member, payment_type, id_request, reschedule_attempts, created_at, updated_at | appointment/models.py:392, appointment/forms.py (write path) |
| appointment.AppointmentRescheduleHistory | AppointmentRescheduleHistory | READ, WRITE | appointment_request, date, start_time, end_time, staff_member, reason_for_rescheduling, reschedule_status, id_request, created_at, updated_at | appointment/models.py:509, appointment/views.py (write path) |
| appointment.Appointment | Appointment | READ, WRITE | client, appointment_request, phone, address, want_reminder, additional_info, paid, amount_to_pay, id_request, created_at, updated_at | appointment/models.py:587, appointment/forms.py (write path) |
| appointment.Config | Config | READ, WRITE | slot_duration, lead_time, finish_time, appointment_buffer_time, website_name, app_offered_by_label, default_reschedule_limit, allow_staff_change_on_reschedule, default_to_service_duration, slot_gap_time, created_at, updated_at | appointment/models.py:830, appointment/tests/test_services.py (write path) |
| appointment.PaymentInfo | PaymentInfo | READ, WRITE | appointment, created_at, updated_at | appointment/models.py:946, appointment/tests/models/test_payment_info.py (write path) |
| appointment.EmailVerificationCode | EmailVerificationCode | READ | user, code, created_at, updated_at | appointment/models.py:996, appointment/services.py (referenced) |
| appointment.PasswordResetToken | PasswordResetToken | READ, WRITE | user, token, expires_at, status, created_at, updated_at | appointment/models.py:1034, appointment/tests/models/test_password_reset_token.py (write path) |
| appointment.DayOff | DayOff | READ, WRITE | staff_member, start_date, end_date, description, created_at, updated_at | appointment/models.py:1127, appointment/tests/test_services.py (write path) |
| appointment.WorkingHours | WorkingHours | READ, WRITE | staff_member, day_of_week, start_time, end_time, created_at, updated_at | appointment/models.py:1154, appointment/forms.py (write path) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
