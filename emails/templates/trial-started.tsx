import * as React from "react";
import { Section, Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, brand, sharedStyles } from "./base.js";

export type TrialStartedProps = {
  firstName?: string;
  trialEndDate: string;
  trialDays?: number;
  appUrl: string;
  unsubscribeUrl?: string;
};

export default function TrialStartedEmail({
  firstName,
  trialEndDate = "March 17, 2026",
  trialDays = 7,
  appUrl = "https://app.sharppicks.ai",
  unsubscribeUrl,
}: TrialStartedProps) {
  return (
    <BaseEmail
      preview="Your SharpPicks trial has started"
      label="Trial"
      title="Trial Activated"
      subtitle={
        firstName
          ? `${firstName}, your ${trialDays}-day SharpPicks trial is now active.`
          : `Your ${trialDays}-day SharpPicks trial is now active.`
      }
      ctaText="Open SharpPicks"
      ctaUrl={appUrl}
      footerNote="SharpPicks — selective by design."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Trial started</Tagline>
      <DataCard>
        <StatRow label="Status" value="Active trial" valueColor={brand.green} />
        <StatRow label="Duration" value={`${trialDays} days`} />
        <StatRow label="Ends" value={trialEndDate} />
      </DataCard>
      <Section style={{
        backgroundColor: brand.panelSoft,
        border: `1px solid ${brand.line}`,
        borderRadius: "12px",
        padding: "18px 20px",
        margin: "0 0 20px",
      }}>
        <Text style={{ ...sharedStyles.copy, margin: "0 0 10px", color: brand.text, fontWeight: 600 }}>
          What to expect
        </Text>
        <Text style={{ ...sharedStyles.copy, margin: "0 0 6px" }}>
          Daily market intelligence scans across the full board.
        </Text>
        <Text style={{ ...sharedStyles.copy, margin: "0 0 6px" }}>
          Signals generated only when real edge is detected.
        </Text>
        <Text style={{ ...sharedStyles.copy, margin: 0 }}>
          Some days produce several signals. Others produce none. That is the system working.
        </Text>
      </Section>
    </BaseEmail>
  );
}
