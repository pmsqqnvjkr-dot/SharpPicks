import { useNavigate } from 'react-router-dom';

export default function Disclaimer() {
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
        }}>Disclaimer</h1>
        <p style={{
          fontSize: '13px',
          color: 'var(--text-tertiary)',
          marginBottom: '32px',
          fontFamily: 'var(--font-mono)',
        }}>Last updated: February 17, 2026</p>

        <div style={{
          backgroundColor: 'rgba(79, 134, 247, 0.06)',
          border: '1px solid rgba(79, 134, 247, 0.15)',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '32px',
        }}>
          <p style={{
            fontSize: '16px',
            lineHeight: 1.7,
            color: 'var(--text-primary)',
            fontWeight: 500,
            fontFamily: 'var(--font-serif)',
          }}>SharpPicks provides sports analytics and model-based insights. This is not financial advice. SharpPicks is not a sportsbook.</p>
        </div>

        <Section title="For Entertainment Purposes Only">
          <p>All content provided by SharpPicks, including but not limited to model predictions, pick analysis, edge calculations, spread comparisons, and performance metrics, is intended for informational and entertainment purposes only.</p>
        </Section>

        <Section title="No Guarantees">
          <p>Past performance of our model does not guarantee future results. Historical records, win rates, ROI figures, and all statistical metrics are based on backtested and live-tracked data. Markets are inherently unpredictable, and no analytical model can guarantee outcomes.</p>
        </Section>

        <Section title="Not a Sportsbook">
          <p>SharpPicks does not accept wagers, facilitate betting, or operate as a sportsbook in any jurisdiction. We do not have partnerships with or receive compensation from any sportsbook operators. We do not use affiliate links.</p>
        </Section>

        <Section title="Personal Responsibility">
          <p>Any decisions you make based on information provided by SharpPicks are entirely your own. You assume full responsibility for any financial risk. SharpPicks, its founder, and its operators are not liable for any losses incurred.</p>
        </Section>

        <Section title="Legal Compliance">
          <p>Sports betting regulations vary by jurisdiction. You are solely responsible for understanding and complying with the laws applicable in your location. Do not use SharpPicks in any manner that would violate local, state, or federal laws.</p>
        </Section>

        <Section title="Age Requirement">
          <p>You must be at least 18 years of age (or the legal age in your jurisdiction) to use SharpPicks. By using the Service, you confirm that you meet this requirement.</p>
        </Section>

        <Section title="Responsible Approach">
          <div style={{
            marginTop: '8px',
            padding: '16px 20px',
            borderLeft: '3px solid var(--green-profit)',
            backgroundColor: 'rgba(52, 211, 153, 0.04)',
          }}>
            <div style={{
              fontFamily: "'Courier New', monospace",
              fontSize: '9px',
              fontWeight: 700,
              letterSpacing: '2.5px',
              textTransform: 'uppercase',
              color: 'var(--green-profit)',
              marginBottom: '8px',
            }}>Sharp Principle</div>
            <p style={{
              fontFamily: 'Georgia, serif',
              fontSize: '16px',
              lineHeight: 1.5,
              color: 'var(--text-primary)',
              fontStyle: 'italic',
              margin: 0,
            }}>The goal is not to chase wins. It is to build a disciplined, data-driven process that stands on its own record.</p>
          </div>
          <p style={{ marginTop: '16px' }}>SharpPicks is designed around discipline and selectivity. Our model passes on the majority of games. This restraint is intentional. If you find yourself chasing losses or wagering beyond your means, we encourage you to seek help.</p>
          <p style={{ marginTop: '12px' }}>
            <strong style={{ color: 'var(--text-primary)' }}>National Problem Gambling Helpline:</strong> 1-800-522-4700
          </p>
        </Section>

        <Section title="Contact">
          <p>Questions about this disclaimer can be directed to:</p>
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
