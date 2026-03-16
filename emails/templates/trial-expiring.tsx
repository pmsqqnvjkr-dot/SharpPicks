import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, sharedStyles } from "./base.js";

export type TrialExpiringProps = {
  firstName?: string;
  daysLeft: number;
  trialEndDate: string;
  upgradeUrl: string;
  unsubscribeUrl?: string;
};

export default function TrialExpiringEmail({
  firstName,
  daysLeft = 2,
  trialEndDate = "March 17, 2026",
  upgradeUrl = "https://app.sharppicks.ai/upgrade",
  unsubscribeUrl,
}: TrialExpiringProps) {
  return (
    <BaseEmail
      preview={`Your SharpPicks trial ends in ${daysLeft} day${daysLeft === 1 ? "" : "s"}`}
      label="Account"
      title="Trial Ending Soon"
      subtitle={
        firstName
          ? `${firstName}, your SharpPicks trial ends on ${trialEndDate}.`
          : `Your SharpPicks trial ends on ${trialEndDate}.`
      }
      ctaText="Continue Access"
      ctaUrl={upgradeUrl}
      footerNote="SharpPicks — disciplined signals, delivered clearly."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Account update</Tagline>
      <DataCard>
        <StatRow label="Days Remaining" value={daysLeft} />
        <StatRow label="Trial Ends" value={trialEndDate} />
        <StatRow label="Access" value="Premium trial" />
      </DataCard>
      <Text style={sharedStyles.copy}>
        Continue your access to model signals, results, and weekly performance
        reporting without interruption.
      </Text>
    </BaseEmail>
  );
}
