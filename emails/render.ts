import { render } from "@react-email/render";
import { createElement } from "react";

const TEMPLATES: Record<string, () => Promise<{ default: React.ComponentType<any> }>> = {
  signal: () => import("./templates/signal.js"),
  result: () => import("./templates/result.js"),
  "weekly-summary": () => import("./templates/weekly-summary.js"),
  "no-signal": () => import("./templates/no-signal.js"),
  "trial-expiring": () => import("./templates/trial-expiring.js"),
  welcome: () => import("./templates/welcome.js"),
  verification: () => import("./templates/verification.js"),
  "password-reset": () => import("./templates/password-reset.js"),
  cancellation: () => import("./templates/cancellation.js"),
  "payment-failed": () => import("./templates/payment-failed.js"),
  "founding-member": () => import("./templates/founding-member.js"),
  "trial-started": () => import("./templates/trial-started.js"),
  "trial-expired": () => import("./templates/trial-expired.js"),
};

async function main() {
  const templateName = process.argv[2];
  if (!templateName) {
    process.stderr.write(
      `Usage: echo '{"key":"val"}' | npx tsx render.ts <template>\nAvailable: ${Object.keys(TEMPLATES).join(", ")}\n`
    );
    process.exit(1);
  }

  const loader = TEMPLATES[templateName];
  if (!loader) {
    process.stderr.write(
      `Unknown template: ${templateName}\nAvailable: ${Object.keys(TEMPLATES).join(", ")}\n`
    );
    process.exit(1);
  }

  let props: Record<string, any> = {};
  const chunks: Buffer[] = [];

  for await (const chunk of process.stdin) {
    chunks.push(Buffer.from(chunk));
  }

  const raw = Buffer.concat(chunks).toString("utf-8").trim();
  if (raw) {
    try {
      props = JSON.parse(raw);
    } catch (e) {
      process.stderr.write(`Invalid JSON on stdin: ${(e as Error).message}\n`);
      process.exit(1);
    }
  }

  const mod = await loader();
  const Component = mod.default;
  const html = await render(createElement(Component, props));
  process.stdout.write(html);
}

main().catch((err) => {
  process.stderr.write(`Render error: ${err.message}\n${err.stack}\n`);
  process.exit(1);
});
