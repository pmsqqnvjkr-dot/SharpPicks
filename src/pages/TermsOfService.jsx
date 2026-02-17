import { useNavigate } from 'react-router-dom';

export default function TermsOfService() {
  const navigate = useNavigate();

  const Section = ({ title, children }) => (
    <div style={{ marginBottom: '28px' }}>
      <h3 style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '16px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '10px',
      }}>{title}</h3>
      <div style={{
        fontSize: '14px',
        lineHeight: 1.8,
        color: 'var(--text-secondary)',
      }}>{children}</div>
    </div>
  );

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      padding: '20px',
    }}>
      <div style={{
        maxWidth: '640px',
        margin: '0 auto',
        padding: '40px 0',
      }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--blue-primary)',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            marginBottom: '24px',
            padding: 0,
            fontFamily: 'var(--font-sans)',
          }}
        >
          &larr; Back
        </button>

        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '28px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '8px',
        }}>Terms of Service</h1>
        <p style={{
          fontSize: '13px',
          color: 'var(--text-tertiary)',
          marginBottom: '32px',
          fontFamily: 'var(--font-mono)',
        }}>Last updated: February 17, 2026</p>

        <Section title="1. Acceptance of Terms">
          <p>By accessing or using SharpPicks (the "Service"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>
        </Section>

        <Section title="2. Description of Service">
          <p>SharpPicks is a sports analytics platform that provides model-based insights and statistical analysis for NBA games. The Service includes pick analysis, pass-day reports, performance tracking, and related features delivered via web and mobile applications.</p>
        </Section>

        <Section title="3. Important Disclaimers">
          <div style={{
            backgroundColor: 'rgba(79, 134, 247, 0.06)',
            border: '1px solid rgba(79, 134, 247, 0.15)',
            borderRadius: '12px',
            padding: '16px 20px',
            marginTop: '8px',
            marginBottom: '12px',
          }}>
            <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>SharpPicks provides sports analytics and model-based insights only. This is not financial advice. SharpPicks is not a sportsbook and does not facilitate wagering.</p>
          </div>
          <p style={{ marginBottom: '12px' }}>Past model performance does not guarantee future results. All statistical metrics, win rates, and historical records are provided for informational and entertainment purposes only.</p>
          <p style={{ marginBottom: '12px' }}>You acknowledge that any decisions you make based on our analysis are your own responsibility. SharpPicks assumes no liability for financial outcomes resulting from the use of our Service.</p>
          <p>Sports betting may not be legal in all jurisdictions. You are solely responsible for ensuring compliance with your local laws.</p>
        </Section>

        <Section title="4. Eligibility">
          <p>You must be at least 18 years of age to use SharpPicks. By using the Service, you represent and warrant that you meet this requirement.</p>
        </Section>

        <Section title="5. Account Registration">
          <p style={{ marginBottom: '12px' }}>You must provide accurate and complete information when creating an account. You are responsible for maintaining the confidentiality of your credentials and for all activities under your account.</p>
          <p>One account per person. Creating multiple accounts to circumvent trial limitations or abuse the Service is prohibited and may result in permanent suspension.</p>
        </Section>

        <Section title="6. Subscriptions and Payments">
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Free Tier:</strong> Limited access to platform features at no cost.</p>
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Trial:</strong> 14-day trial with full access. Requires a valid payment method on file. You will be charged at the end of the trial period unless you cancel beforehand.</p>
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Paid Subscription:</strong> Billed monthly or annually via Stripe. You may cancel at any time. Access continues through the end of the current billing period.</p>
          <p>All payments are processed by Stripe. Refund requests should be directed to support@sharppicks.ai within 7 days of charge.</p>
        </Section>

        <Section title="7. Acceptable Use">
          <p>You agree not to:</p>
          <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
            <li>Share, redistribute, or resell SharpPicks content or analysis</li>
            <li>Scrape, crawl, or automated access the Service</li>
            <li>Attempt to reverse-engineer the model or algorithms</li>
            <li>Use the Service to harass, abuse, or harm others</li>
            <li>Create multiple accounts or circumvent access controls</li>
            <li>Misrepresent your identity or affiliation</li>
          </ul>
        </Section>

        <Section title="8. Intellectual Property">
          <p>All content, analysis, models, algorithms, branding, and design on SharpPicks are the intellectual property of SharpPicks and its founder. You may not reproduce, distribute, or create derivative works without explicit written permission.</p>
        </Section>

        <Section title="9. Termination">
          <p>We reserve the right to suspend or terminate your account at any time for violations of these Terms, abusive behavior, or any reason at our sole discretion. Upon termination, your right to access the Service ceases immediately.</p>
        </Section>

        <Section title="10. Limitation of Liability">
          <p>To the fullest extent permitted by law, SharpPicks and its operators shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising out of your use of the Service, including but not limited to financial losses from wagering decisions.</p>
        </Section>

        <Section title="11. Changes to Terms">
          <p>We may update these Terms from time to time. Continued use of the Service after changes constitutes acceptance of the revised Terms. We encourage you to review this page periodically.</p>
        </Section>

        <Section title="12. Governing Law">
          <p>These Terms shall be governed by and construed in accordance with the laws of the United States, without regard to conflict of law principles.</p>
        </Section>

        <Section title="13. Contact">
          <p>For questions about these Terms, contact us at:</p>
          <p style={{ marginTop: '8px' }}>
            <strong style={{ color: 'var(--text-primary)' }}>Email:</strong> support@sharppicks.ai<br />
            <strong style={{ color: 'var(--text-primary)' }}>Website:</strong> app.sharppicks.ai
          </p>
        </Section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--stroke-subtle)', margin: '32px 0' }} />
        <p style={{
          fontSize: '12px',
          color: 'var(--text-tertiary)',
          textAlign: 'center',
        }}>SharpPicks — Discipline is the edge.</p>
      </div>
    </div>
  );
}
