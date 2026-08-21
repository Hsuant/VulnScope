// Profile page (ProfileView.vue)
export default {
  headerDesc: 'View and edit your account information',
  editProfile: 'Edit Profile',
  accountInfo: 'Account Info',
  accountStatus: 'Account Status',
  changePassword: 'Change Password',
  usernameReadonly: 'Username cannot be changed',
  passwordHint: 'At least 8 characters',
  saving: 'Saving...',
  saveChanges: 'Save Changes',
  active: 'Active',
  disabled: 'Disabled',
  lastLogin: 'Last Login',
  registeredAt: 'Registered',
  fields: {
    username: 'Username',
    email: 'Email',
    newPassword: 'New Password',
    confirmPassword: 'Confirm Password',
    role: 'Role',
  },
  placeholders: {
    email: 'Enter your email',
    newPassword: 'Leave blank to keep current',
    confirmPassword: 'Re-enter new password',
  },
  rules: {
    email: 'Please enter a valid email address',
    passwordMin: 'Password must be at least 8 chars',
    passwordMismatch: 'The two passwords do not match',
  },
  messages: {
    noChanges: 'Nothing to update',
    updated: 'Profile updated',
  },
}
