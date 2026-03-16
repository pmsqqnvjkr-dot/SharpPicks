import * as React from "react";
import {
  Body,
  Button,
  Column,
  Container,
  Head,
  Heading,
  Hr,
  Html,
  Img,
  Preview,
  Row,
  Section,
  Text,
} from "@react-email/components";

// Legacy / brand design: dark panel, crest logo, green CTA, Arial
export const brand = {
  bg: "#0D0D0D",
  panel: "#141414",
  panelSoft: "#1A1A1A",
  line: "#2A2A2A",
  text: "#FFFFFF",
  textMuted: "#AAAAAA",
  label: "#666666",
  footer: "#444444",
  link: "#4A9EFF",
  green: "#5A9E72",
  blue: "#3BA3FF",
  red: "#CC3333",
  amber: "#666666",
  maxWidth: "560px",
  radius: "8px",
};

export const sharedStyles = {
  body: {
    margin: 0,
    padding: 0,
    backgroundColor: brand.bg,
    color: brand.text,
    fontFamily: "Arial, Helvetica, sans-serif",
  },
  container: {
    maxWidth: brand.maxWidth,
    margin: "0 auto",
  },
  shell: {
    backgroundColor: brand.panel,
    borderRadius: brand.radius,
    maxWidth: brand.maxWidth,
    margin: "0 auto",
  },
  inner: {
    padding: "32px 32px 0",
  },
  logoRow: {
    textAlign: "center" as const,
    padding: "0 0 16px",
  },
  logoImg: {
    display: "inline-block",
    verticalAlign: "middle",
    marginRight: 12,
    width: 28,
    height: 28,
  },
  logoText: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "13px",
    fontWeight: 800,
    letterSpacing: "0.3em",
    textTransform: "uppercase" as const,
    color: brand.text,
    verticalAlign: "middle" as const,
    margin: 0,
  },
  logoDivider: {
    border: "none",
    borderTop: `1px solid ${brand.line}`,
    margin: "0 0 24px",
  },
  typeLabel: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "11px",
    fontWeight: 700,
    letterSpacing: "0.1em",
    textTransform: "uppercase" as const,
    color: brand.label,
    margin: "0 0 20px",
  },
  heading: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "22px",
    fontWeight: 700,
    color: brand.text,
    margin: "0 0 18px",
  },
  subheading: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "15px",
    color: brand.textMuted,
    lineHeight: 1.7,
    margin: "0 0 22px",
  },
  copy: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "14px",
    color: brand.textMuted,
    lineHeight: 1.7,
    margin: "0 0 22px",
  },
  button: {
    backgroundColor: brand.green,
    borderRadius: "6px",
    color: brand.text,
    display: "inline-block",
    fontSize: "14px",
    fontWeight: 700,
    letterSpacing: "0.05em",
    padding: "14px 32px",
    textDecoration: "none",
    textTransform: "uppercase" as const,
    fontFamily: "Arial, Helvetica, sans-serif",
  },
  finePrint: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "12px",
    color: brand.label,
    lineHeight: 1.6,
    margin: "0 0 24px",
  },
  footerWrap: {
    padding: "0 32px 32px",
  },
  footerHr: {
    border: "none",
    borderTop: `1px solid ${brand.line}`,
    margin: "24px 0 16px",
  },
  footerText: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "12px",
    color: brand.footer,
    textAlign: "center" as const,
    margin: "0",
  },
  footerLink: {
    color: brand.link,
    textDecoration: "underline",
  },
  card: {
    backgroundColor: brand.panelSoft,
    border: `1px solid ${brand.line}`,
    borderRadius: "6px",
    padding: "16px 18px",
    margin: "0 0 20px",
  },
  rowLabel: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "13px",
    color: brand.textMuted,
    padding: "4px 0",
  },
  rowValue: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "13px",
    color: brand.text,
    padding: "4px 0",
  },
  microTag: {
    display: "inline-block" as const,
    border: `1px solid ${brand.line}`,
    borderRadius: "999px",
    padding: "6px 10px",
    color: brand.textMuted,
    fontSize: "11px",
    letterSpacing: "1px",
    textTransform: "uppercase" as const,
    marginBottom: "16px",
  },
};

type BaseEmailProps = {
  preview: string;
  label: string;
  title?: string;
  subtitle?: string;
  ctaText?: string;
  ctaUrl?: string;
  ctaColor?: string;
  finePrint?: string;
  children: React.ReactNode;
  footerNote?: string;
  unsubscribeUrl?: string;
  appUrl?: string;
};

export function BaseEmail({
  preview,
  label,
  title,
  subtitle,
  ctaText,
  ctaUrl,
  ctaColor,
  finePrint,
  children,
  footerNote = "SharpPicks — Discipline is the product.",
  unsubscribeUrl = "",
  appUrl = "https://app.sharppicks.ai",
}: BaseEmailProps) {
  const logoUrl = `${appUrl.replace(/\/$/, "")}/images/crest.png`;
  const buttonStyle = { ...sharedStyles.button, backgroundColor: ctaColor || brand.green };
  return (
    <Html>
      <Head />
      <Preview>{preview}</Preview>
      <Body style={sharedStyles.body}>
        <Container style={{ ...sharedStyles.container, padding: "32px 16px" }}>
          <Section style={sharedStyles.shell}>
            <Section style={sharedStyles.inner}>
              <Section style={sharedStyles.logoRow}>
                <Img
                  src={logoUrl}
                  alt=""
                  width={28}
                  height={28}
                  style={sharedStyles.logoImg}
                />
                <Text style={sharedStyles.logoText}>
                  SHARP<span style={{ opacity: 0.5, margin: "0 0.35em", fontWeight: 500, letterSpacing: "0.15em" }}>||</span>PICKS
                </Text>
              </Section>
              <Hr style={sharedStyles.logoDivider} />

              <Section style={{ padding: "0 32px" }}>
                <Text style={sharedStyles.typeLabel}>{label}</Text>
                {title ? (
                  <Heading as="h1" style={sharedStyles.heading}>
                    {title}
                  </Heading>
                ) : null}
                {subtitle ? (
                  <Text style={sharedStyles.subheading}>{subtitle}</Text>
                ) : null}

                {children}

                {ctaText && ctaUrl ? (
                  <Section style={{ margin: "32px auto", textAlign: "center" as const }}>
                    <Button href={ctaUrl} style={buttonStyle}>
                      {ctaText}
                    </Button>
                  </Section>
                ) : null}
                {finePrint ? (
                  <Text style={sharedStyles.finePrint}>{finePrint}</Text>
                ) : null}
              </Section>

              <Section style={sharedStyles.footerWrap}>
                <Hr style={sharedStyles.footerHr} />
                <Text style={sharedStyles.footerText}>{footerNote}</Text>
                <Text style={{ ...sharedStyles.footerText, marginTop: "8px" }}>
                  <a href="mailto:support@sharppicks.ai" style={sharedStyles.footerLink}>
                    support@sharppicks.ai
                  </a>
                </Text>
                {unsubscribeUrl ? (
                  <Text style={{ ...sharedStyles.footerText, marginTop: "8px" }}>
                    <a href={unsubscribeUrl} style={sharedStyles.footerLink}>
                      Unsubscribe
                    </a>
                  </Text>
                ) : null}
              </Section>
            </Section>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

type StatRowProps = {
  label: string;
  value: string | number;
  valueColor?: string;
};

export function StatRow({ label, value, valueColor }: StatRowProps) {
  return (
    <Row>
      <Column>
        <Text style={sharedStyles.rowLabel}>{label}</Text>
      </Column>
      <Column>
        <Text
          style={{
            ...sharedStyles.rowValue,
            color: valueColor || brand.text,
          }}
        >
          {value}
        </Text>
      </Column>
    </Row>
  );
}

export function DataCard({ children }: { children: React.ReactNode }) {
  return <Section style={sharedStyles.card}>{children}</Section>;
}

export function Tagline({ children }: { children: React.ReactNode }) {
  return <Text style={sharedStyles.microTag}>{children}</Text>;
}
