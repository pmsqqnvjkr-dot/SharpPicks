import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, Tagline, sharedStyles } from "./base.js";

export type PasswordResetProps = {
  firstName?: string;
  resetUrl: string;
  expiresIn?: string;
};

export default function PasswordResetEmail({
  firstName,
  resetUrl = "https://app.sharppicks.ai/reset",
  expiresIn = "1 hour",
}: PasswordResetProps) {
  return (
    <BaseEmail
      preview="Reset your SharpPicks password"
      label="Security"
      title="Password Reset"
      subtitle={
        firstName
          ? `${firstName}, a password reset was requested for your account.`
          : "A password reset was requested for your account."
      }
      ctaText="Reset Password"
      ctaUrl={resetUrl}
      footerNote="SharpPicks — account security."
    >
      <Tagline>Security update</Tagline>
      <Text style={sharedStyles.copy}>
        Click the button above to set a new password. This link expires in {expiresIn}.
      </Text>
      <Text style={sharedStyles.copy}>
        If you did not request a password reset, no action is needed. Your account remains secure.
      </Text>
    </BaseEmail>
  );
}
