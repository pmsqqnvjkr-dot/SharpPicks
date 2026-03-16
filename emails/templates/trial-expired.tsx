import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, brand, sharedStyles } from "./base.js";

export type TrialExpiredProps = {
  firstName?: string;
  signalsDelivered?: number;
  upgradeUrl: string;
  unsubscribeUrl?: string;
};

export default function TrialExpiredEmail({
  firstName,
  signalsDelivered,
  upgradeUrl = "https://app.sharppicks.ai/upgrade",
  unsubscribeUrl,
}: TrialExpiredProps) {
  return (
    <BaseEmail
      preview="Your SharpPicks trial has ended"
      label="Account"
      title="Trial Ended"
      subtitle={
        firstName
          ? `${firstName}, your SharpPicks trial has ended.`
          : "Your SharpPicks trial has ended."
      }
      ctaText="Continue Access"
      ctaUrl={upgradeUrl}
      footerNote="SharpPicks — selective by design."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Account update</Tagline>
      <DataCard>
        <StatRow label="Status" value="Trial ended" valueColor={brand.amber} />
        {signalsDelivered != null ? (
          <StatRow label="Signals Delivered" value={signalsDelivered} />
        ) : null}
      </DataCard>
      <Text style={sharedStyles.copy}>
        Your trial period has concluded. Upgrade to maintain access to model signals,
        market intelligence, and performance tracking.
      </Text>
      <Text style={{ ...sharedStyles.copy, fontStyle: "italic" }}>
        Beat the market, not the scoreboard.
      </Text>
    </BaseEmail>
  );
}
