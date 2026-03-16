import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, sharedStyles } from "./base.js";

export type VerificationProps = {
  firstName?: string;
  verifyUrl: string;
  code?: string;
};

export default function VerificationEmail({
  firstName,
  verifyUrl = "https://app.sharppicks.ai/verify",
  code,
}: VerificationProps) {
  return (
    <BaseEmail
      preview="Verify your SharpPicks email"
      label="Verification"
      title="Verify Your Email"
      subtitle={
        firstName
          ? `${firstName}, confirm your email address to activate your SharpPicks account.`
          : "Confirm your email address to activate your SharpPicks account."
      }
      ctaText="Verify Email"
      ctaUrl={verifyUrl}
      footerNote="SharpPicks — account security."
    >
      <Tagline>Account setup</Tagline>
      {code ? (
        <DataCard>
          <StatRow label="Verification Code" value={code} />
        </DataCard>
      ) : null}
      <Text style={sharedStyles.copy}>
        If you did not create a SharpPicks account, you can safely ignore this email.
      </Text>
    </BaseEmail>
  );
}
