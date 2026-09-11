-- Add the built-in account email templates without replacing administrator customisations.
INSERT INTO message_templates (slug, name, description, content_type, content)
SELECT
  'staff_invitation',
  'Staff Invitation',
  'Sent to staff when they are invited to activate their portal account.',
  'text/html',
  '<p>Hello {{ user.name }},</p><p>You''ve been invited to access {{ app.name }}.</p><p><a href="{{ invitation.link }}">Set your password and activate your account</a></p><p>The link expires in 7 days. If you were not expecting this invitation you can ignore this email.</p>'
WHERE NOT EXISTS (
  SELECT 1 FROM message_templates WHERE slug = 'staff_invitation'
);

INSERT INTO message_templates (slug, name, description, content_type, content)
SELECT
  'signup_verification',
  'Email Verification',
  'Sent to new users so they can verify their email address before signing in.',
  'text/html',
  '<p>Hello {{ user.name }},</p><p>Thanks for signing up for {{ app.name }}. Please verify your email address before signing in.</p><p><a href="{{ verification.link }}">Verify your signup</a></p><p>This link expires in 24 hours. If you did not create this account, you can ignore this email.</p>'
WHERE NOT EXISTS (
  SELECT 1 FROM message_templates WHERE slug = 'signup_verification'
);
