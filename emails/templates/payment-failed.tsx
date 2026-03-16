import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, brand, sharedStyles } from "./base.js";

export type PaymentFailedProps = {
  firstName?: string;
  retryDate?: string;
  updateUrl: string;
  unsubscribeUrl?: string;
};

export default function PaymentFailedEmail({
  firstName,
  retryDate,
  updateUrl = "https://app.sharppicks.ai/account",
  unsubscribeUrl,
}: PaymentFailedProps) {
  return (
    <BaseEmail
      preview="Payment issue with your SharpPicks account"
      label="Billing"
      title="Payment Failed"
      subtitle={
        firstName
          ? `${firstName}, we were unable to process your most recent payment.`
          : "We were unable to process your most recent payment."
      }
      ctaText="Update Payment"
      ctaUrl={updateUrl}
      footerNote="SharpPicks — account communication."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Billing update</Tagline>
      <DataCard>
        <StatRow label="Status" value="Payment failed" valueColor={brand.amber} />
        {retryDate ? <StatRow label="Next Retry" value={retryDate} /> : null}
      </DataCard>
      <Text style={sharedStyles.copy}>
        Please update your payment method to maintain uninterrupted access to SharpPicks
        signals and performance data.
      </Text>
    </BaseEmail>
  );
}
