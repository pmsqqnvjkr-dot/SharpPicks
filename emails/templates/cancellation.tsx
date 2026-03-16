import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, sharedStyles } from "./base.js";

export type CancellationProps = {
  firstName?: string;
  accessEndsDate: string;
  reactivateUrl: string;
  unsubscribeUrl?: string;
};

export default function CancellationEmail({
  firstName,
  accessEndsDate = "April 1, 2026",
  reactivateUrl = "https://app.sharppicks.ai/upgrade",
  unsubscribeUrl,
}: CancellationProps) {
  return (
    <BaseEmail
      preview="Your SharpPicks subscription has been cancelled"
      label="Account"
      title="Subscription Cancelled"
      subtitle={
        firstName
          ? `${firstName}, your subscription has been cancelled. You retain access through the end of your billing period.`
          : "Your subscription has been cancelled. You retain access through the end of your billing period."
      }
      ctaText="Reactivate"
      ctaUrl={reactivateUrl}
      footerNote="SharpPicks — always here when you're ready."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Account update</Tagline>
      <DataCard>
        <StatRow label="Status" value="Cancelled" />
        <StatRow label="Access Until" value={accessEndsDate} />
      </DataCard>
      <Text style={sharedStyles.copy}>
        Your access to model signals and performance data continues until the date above.
        You can reactivate at any time to resume uninterrupted service.
      </Text>
    </BaseEmail>
  );
}
