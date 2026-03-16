import * as React from "react";
import { Section, Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, brand, sharedStyles } from "./base.js";

export type FoundingMemberProps = {
  firstName?: string;
  foundingNumber?: number;
  appUrl: string;
  unsubscribeUrl?: string;
};

export default function FoundingMemberEmail({
  firstName,
  foundingNumber,
  appUrl = "https://app.sharppicks.ai",
  unsubscribeUrl,
}: FoundingMemberProps) {
  return (
    <BaseEmail
      preview="You're a SharpPicks Founding Member"
      label="Founding Member"
      title="Founding Status Confirmed"
      subtitle={
        firstName
          ? `${firstName}, you are now a SharpPicks Founding Member.`
          : "You are now a SharpPicks Founding Member."
      }
      ctaText="Open SharpPicks"
      ctaUrl={appUrl}
      footerNote="SharpPicks — selective by design."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Founding Member</Tagline>
      <DataCard>
        <StatRow label="Status" value="Founding Member" valueColor={brand.green} />
        {foundingNumber ? <StatRow label="Member #" value={`#${foundingNumber}`} /> : null}
        <StatRow label="Access" value="Lifetime Premium" />
      </DataCard>
      <Section style={{
        backgroundColor: brand.panelSoft,
        border: `1px solid ${brand.line}`,
        borderRadius: "12px",
        padding: "18px 20px",
        margin: "0 0 20px",
      }}>
        <Text style={{ ...sharedStyles.copy, margin: "0 0 10px", color: brand.text }}>
          As a Founding Member, you helped build the foundation of SharpPicks.
        </Text>
        <Text style={{ ...sharedStyles.copy, margin: 0, fontStyle: "italic" }}>
          Discipline is the product.
        </Text>
      </Section>
    </BaseEmail>
  );
}
