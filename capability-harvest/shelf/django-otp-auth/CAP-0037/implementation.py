# Harvested by harvest_parts.py
# capability : CAP-0037 (verify phone)
# from       : django-otp-auth @ b67bc6848aceca230c4b84e4c22357c8870f2b04
# source     : otp/django_otp_auth/apps/rest/auth/views.py:52-62
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def post(self, request):
        serializer = VerifyOtpRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            if OTPCode.objects.is_valid(data['receiver'], data['uuid'], data['code']):
                response_data = self._handle_login(data, request)
                print(response_data)
                return Response(response_data)
            return Response(err_msg('کد ارسال شده درست نمیباشد', 400), status=status.HTTP_400_BAD_REQUEST)

        return Response(err_msg(err_serializer(serializer.errors), 400), status=status.HTTP_400_BAD_REQUEST)
