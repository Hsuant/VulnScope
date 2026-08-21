// User management page (UserManageView.vue)
export default {
  createUser: 'New User',
  editUser: 'Edit User',
  columns: {
    username: 'Username',
    email: 'Email',
    role: 'Role',
    lastLogin: 'Last Login',
    createdAt: 'Created',
  },
  fields: {
    username: 'Username',
    email: 'Email',
    password: 'Password',
    role: 'Role',
    active: 'Active',
  },
  placeholders: {
    username: '3-64 chars, letters, digits, _ . -',
    emailOptional: 'Optional',
    passwordEdit: 'Leave blank to keep',
    passwordNew: 'At least 8 chars',
  },
  rules: {
    usernameRequired: 'Please enter a username',
    usernamePattern: '3-64 chars: letters, digits, underscore, hyphen only',
    passwordRequired: 'Please enter a password',
    passwordMin: 'Password must be at least 8 chars',
  },
  messages: {
    updateSuccess: 'User updated',
    createSuccess: 'User created',
    deleteSuccess: 'User deleted',
  },
}
