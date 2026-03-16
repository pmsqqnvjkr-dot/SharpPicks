import * as React from "react";
import { Section, Text } from "@react-email/components";
import { BaseEmail, brand, sharedStyles } from "./base.js";

const accentBlue = brand.blue || "#3BA3FF";
const panelDark = "#11161D";
const textLight = "#e0e0e0";
const textMuted = "#b8b8b8";
const textSecondary = "#888888";

const steps = [
  {
    title: "Set Your Unit Size",
    description: "Discipline starts with bankroll management.",
  },
  {
    title: "Explore Today's Analysis",
    description: "See what the model found — or why it passed.",
  },
  {
    title: "Review the Public Record",
    description: "Every pick and pass tracked transparently — verified by data, not talk.",
  },
];

export type WelcomeProps = {
  firstName?: string;
  appUrl: string;
  unsubscribeUrl?: string;
};

export default function WelcomeEmail({
  firstName,
  appUrl = "https://app.sharppicks.ai",
  unsubscribeUrl,
}: WelcomeProps) {
  const name = firstName || "there";
  return (
    <BaseEmail
      preview="Welcome to SharpPicks — sports market intelligence"
      label="Welcome"
      title={`Hi ${name},`}
      subtitle=""
      ctaText="ACCESS YOUR DASHBOARD"
      ctaUrl={appUrl}
      ctaColor={accentBlue}
      footerNote="SharpPicks — Discipline is the product."
      unsubscribeUrl={unsubscribeUrl}
      appUrl={appUrl}
    >
      <Text style={{ ...sharedStyles.copy, color: textMuted, margin: "0 0 24px" }}>
        Welcome to SharpPicks.
      </Text>
      <Text style={{ ...sharedStyles.copy, color: textMuted, margin: "0 0 24px" }}>
        Most people treat sports betting like a game of luck. We treat it like a market. By joining this community, you've chosen to move away from the noise and toward a data-driven, disciplined approach.
      </Text>
      <Text style={{ ...sharedStyles.copy, color: textMuted, margin: "0 0 24px" }}>
        Evan Cole here. I built this platform because I was tired of the "hype" culture. I wanted a tool that prioritized institutional-grade tracking and transparency over flashy promos.
      </Text>
      <Text style={{ ...sharedStyles.copy, color: textLight, fontWeight: 600, margin: "0 0 16px" }}>
        Here is how to get the most out of your first 24 hours:
      </Text>

      <Section style={{ margin: "0 0 28px" }}>
        {steps.map((step, i) => (
          <Section
            key={i}
            style={{
              padding: "14px 16px",
              borderBottom: i < steps.length - 1 ? `1px solid #1a1d28` : "none",
            }}
          >
            <Text style={{ margin: "0 0 4px", fontSize: "14px", fontWeight: 700, color: accentBlue }}>
              {i + 1}.
            </Text>
            <Text style={{ margin: "0 0 4px", fontSize: "15px", fontWeight: 600, color: textLight }}>
              {step.title}
            </Text>
            <Text style={{ margin: "0 0 0 22px", fontSize: "13px", color: textSecondary, lineHeight: 1.6 }}>
              {step.description}
            </Text>
          </Section>
        ))}
      </Section>

      <Section
        style={{
          margin: "28px 0 28px",
          padding: "20px 24px",
          borderLeft: `3px solid ${accentBlue}`,
          backgroundColor: "rgba(59, 163, 255, 0.04)",
        }}
      >
        <Text
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            fontSize: "9px",
            fontWeight: 700,
            letterSpacing: "2.5px",
            textTransform: "uppercase",
            color: accentBlue,
            margin: "0 0 14px",
          }}
        >
          Sharp Principle
        </Text>
        <Text
          style={{
            fontFamily: "Georgia, Times New Roman, serif",
            fontSize: "19px",
            lineHeight: 1.55,
            color: textLight,
            fontWeight: 500,
            fontStyle: "italic",
            margin: 0,
          }}
        >
          The goal isn't just to win a bet; it's to build a sustainable edge.
        </Text>
      </Section>

      <Text style={{ ...sharedStyles.copy, color: textMuted, margin: "0 0 32px" }}>
        If you have questions or feedback on the interface, reply directly to this email. I'm personally looking for ways to make our tools sharper for you.
      </Text>
      <Text style={{ ...sharedStyles.copy, color: textMuted, margin: "0 0 4px" }}>
        To the edge,
      </Text>
    </BaseEmail>
  );
}
