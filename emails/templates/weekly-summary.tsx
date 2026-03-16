import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, brand, sharedStyles } from "./base.js";

export type WeeklySummaryProps = {
  firstName?: string;
  record: string;
  roi: string;
  units: string;
  passes: string | number;
  avgEdge?: string;
  totalRecord?: string;
  periodLabel?: string;
  appUrl: string;
  unsubscribeUrl?: string;
};

export default function WeeklySummaryEmail({
  firstName,
  record = "3-1",
  roi = "+18.4%",
  units = "+2.7u",
  passes = 2,
  avgEdge,
  totalRecord,
  periodLabel = "This Week",
  appUrl = "https://app.sharppicks.ai",
  unsubscribeUrl,
}: WeeklySummaryProps) {
  const roiColor = roi.startsWith("-") ? brand.red : brand.green;
  const unitsColor = units.startsWith("-") ? brand.red : brand.green;

  return (
    <BaseEmail
      preview="Weekly performance report"
      label="Weekly Report"
      title={`${periodLabel} Performance`}
      subtitle={
        firstName
          ? `Here is your latest SharpPicks recap, ${firstName}.`
          : "Here is your latest SharpPicks recap."
      }
      ctaText="Open Dashboard"
      ctaUrl={appUrl}
      footerNote="SharpPicks — selective by design."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Data-first recap</Tagline>
      <DataCard>
        <StatRow label="Record" value={record} />
        <StatRow label="ROI" value={roi} valueColor={roiColor} />
        <StatRow label="Units" value={units} valueColor={unitsColor} />
        <StatRow label="Pass Days" value={passes} />
        {avgEdge ? <StatRow label="Avg Edge" value={avgEdge} /> : null}
        {totalRecord ? <StatRow label="Season" value={totalRecord} /> : null}
      </DataCard>
      <Text style={sharedStyles.copy}>
        The weekly report reflects closed results and pass days across the completed period.
      </Text>
    </BaseEmail>
  );
}
