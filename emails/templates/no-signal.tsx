import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, sharedStyles } from "./base.js";

export type NoSignalProps = {
  gamesAnalyzed: string | number;
  edgesDetected: string | number;
  qualifiedSignals: string | number;
  efficiency?: string;
  closestEdge?: string;
  appUrl: string;
  unsubscribeUrl?: string;
};

export default function NoSignalEmail({
  gamesAnalyzed = 9,
  edgesDetected = 2,
  qualifiedSignals = 0,
  efficiency,
  closestEdge,
  appUrl = "https://app.sharppicks.ai",
  unsubscribeUrl,
}: NoSignalProps) {
  return (
    <BaseEmail
      preview="Market scan complete — no signal"
      label="Market Scan"
      title="No Signal Today"
      subtitle="The model completed its scan and did not identify a release-worthy signal."
      ctaText="Open SharpPicks"
      ctaUrl={appUrl}
      footerNote="SharpPicks — no edge, no pick."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Discipline over volume</Tagline>
      <DataCard>
        <StatRow label="Games Analyzed" value={gamesAnalyzed} />
        <StatRow label="Edges Detected" value={edgesDetected} />
        <StatRow label="Qualified Signals" value={qualifiedSignals} />
        {efficiency ? <StatRow label="Efficiency" value={efficiency} /> : null}
        {closestEdge ? <StatRow label="Closest Edge" value={closestEdge} /> : null}
      </DataCard>
      <Text style={sharedStyles.copy}>
        SharpPicks only publishes signals that meet release thresholds. When the
        edge is not there, the product stays quiet. Capital preserved.
      </Text>
    </BaseEmail>
  );
}
