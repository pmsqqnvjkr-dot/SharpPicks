import * as React from "react";
import { Text } from "@react-email/components";
import { BaseEmail, DataCard, StatRow, Tagline, brand, sharedStyles } from "./base.js";

export type ResultProps = {
  matchup: string;
  market: string;
  closeLine?: string;
  clv?: string;
  result: "WIN" | "LOSS" | "PUSH";
  units: string;
  analysis?: string;
  appUrl: string;
  unsubscribeUrl?: string;
};

export default function ResultEmail({
  matchup = "Celtics vs Heat",
  market = "Celtics -4.5",
  closeLine,
  clv,
  result = "WIN",
  units = "+1.0u",
  analysis,
  appUrl = "https://app.sharppicks.ai",
  unsubscribeUrl,
}: ResultProps) {
  const resultColor =
    result === "WIN" ? brand.green : result === "LOSS" ? brand.red : brand.amber;

  return (
    <BaseEmail
      preview={`Result — ${result}`}
      label="Result"
      title={`Result: ${result}`}
      subtitle="A previously published SharpPicks signal has been graded."
      ctaText="Review in App"
      ctaUrl={appUrl}
      footerNote="SharpPicks — process over hype."
      unsubscribeUrl={unsubscribeUrl}
    >
      <Tagline>Discipline is the product</Tagline>
      <DataCard>
        <StatRow label="Game" value={matchup} />
        <StatRow label="Pick" value={market} />
        {closeLine ? <StatRow label="Closing" value={closeLine} /> : null}
        {clv ? <StatRow label="CLV" value={clv} valueColor={clv.startsWith("+") ? brand.green : brand.red} /> : null}
        <StatRow label="Result" value={result} valueColor={resultColor} />
        <StatRow label="Units" value={units} valueColor={resultColor} />
      </DataCard>
      <Text style={sharedStyles.copy}>
        {analysis ||
          "This result has been finalized and added to current SharpPicks performance tracking."}
      </Text>
    </BaseEmail>
  );
}
