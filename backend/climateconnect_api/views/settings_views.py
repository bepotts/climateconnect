import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from django.contrib.auth.models import User
from climateconnect_api.models import UserProfile
from climateconnect_api.permissions import UserPermission
from climateconnect_api.serializers.user import UserAccountSettingsSerializer
from climateconnect_api.utility.email_setup import send_new_email_verification

class UserAccountSettingsView(APIView):
    permission_classes = [UserPermission]

    def get(self, request):
        user = request.user
        serializer = UserAccountSettingsSerializer(user.user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        # set and confirm password.
        if 'password' in request.data and 'confirm_password' in request.data \
                and 'old_password' in request.data:
            check_existing_password = user.check_password(request.data['old_password'])
            if check_existing_password:
                if request.data['password'] == request.data['confirm_password']:
                    user.set_password(request.data['password'])
                    user.save()
                else:
                    raise ValidationError('Password do not match.')
            else:
                raise ValidationError('Incorrect password. Did you forget your password?')

        if 'email' in request.data:
            # TODO: Add email confirmation method.
            new_verification_key = uuid.uuid4()
            user.user_profile.verification_key = new_verification_key
            user.user_profile.pending_new_email = request.data['email']
            send_new_email_verification(user, request.data['email'], new_verification_key)
            user.user_profile.save()

        if 'email_updates_on_projects' in request.data and 'email_project_suggestions' in request.data:
            user.user_profile.email_updates_on_projects = request.data['email_updates_on_projects']
            user.user_profile.email_project_suggestions = request.data['email_project_suggestions']
            user.user_profile.save()

        return Response({'message': 'Account successfully updated'}, status=status.HTTP_200_OK)

class ChangeEmailView(APIView):
    permission_classes = [UserPermission]

    def post(self, request):
        if 'uuid' not in request.data:
            return Response({'message': 'Required parameters are missing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        verification_key = request.data['uuid'].replace('%2D', '-')

        try:
            user_profile = UserProfile.objects.get(user=request.user, verification_key=verification_key)
        except User.DoesNotExist:
            return Response({'message': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user_profile.pending_new_email:
            user_profile.user.email = user_profile.pending_new_email
            user_profile.pending_new_email = None
            user_profile.save()
            user_profile.user.save()
        else:
            return Response({'message': 'No pending E-Mail change. This link may already have been used.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Your E-Mail address is now "+user_profile.user.email}, status=status.HTTP_200_OK)