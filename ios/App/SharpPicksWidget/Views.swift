//
//  Views.swift
//  Three widget sizes plus shared design tokens.
//

import SwiftUI
import WidgetKit

// MARK: - Brand tokens

enum SP {
    static let bg = Color(red: 0x0A/255, green: 0x0D/255, blue: 0x14/255)
    static let surface = Color(red: 0x12/255, green: 0x17/255, blue: 0x25/255)
    static let signalBlue = Color(red: 0x4F/255, green: 0x86/255, blue: 0xF7/255)
    static let edgeGreen = Color(red: 0x34/255, green: 0xD3/255, blue: 0x99/255)
    static let textPrimary = Color(red: 0xE5/255, green: 0xE7/255, blue: 0xEB/255)
    static let textSecondary = Color(red: 0x9C/255, green: 0xA3/255, blue: 0xAF/255)
    static let amber = Color(red: 0xF5/255, green: 0x9E/255, blue: 0x0B/255)
    static let dividerOpacity: Double = 0.15
}

// iOS 17 introduced .containerBackground for widgets and made the
// older .background pattern paint over the system container. This
// modifier picks the right path for the current OS so the widget
// renders correctly on both.

struct WidgetBackground: ViewModifier {
    func body(content: Content) -> some View {
        if #available(iOSApplicationExtension 17.0, *) {
            content.containerBackground(for: .widget) { SP.bg }
        } else {
            content.background(SP.bg)
        }
    }
}

extension View {
    func widgetBg() -> some View { modifier(WidgetBackground()) }
}

// MARK: - Shared status summary (left half of every size)

struct StatusSummary: View {
    let entry: WidgetEntry

    var body: some View {
        VStack(spacing: 8) {
            Text("TODAY")
                .font(.system(size: 9, weight: .bold))
                .tracking(2.5)
                .foregroundColor(SP.textSecondary)

            Spacer(minLength: 4)

            statusBadge

            Spacer(minLength: 4)

            if let mei = entry.mei {
                VStack(spacing: 2) {
                    Text("\(mei)")
                        .font(.system(size: 28, weight: .bold, design: .monospaced))
                        .foregroundColor(SP.textPrimary)
                    Text("MEI")
                        .font(.system(size: 8, weight: .bold))
                        .tracking(2.5)
                        .foregroundColor(SP.textSecondary)
                }
            }

            if let regime = entry.regime {
                Text(regime.uppercased())
                    .font(.system(size: 8, weight: .bold))
                    .tracking(2.0)
                    .foregroundColor(SP.textSecondary)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    @ViewBuilder
    private var statusBadge: some View {
        switch entry.status {
        case .qualifiedEdge:
            Text("QUALIFIED\nEDGE")
                .multilineTextAlignment(.center)
                .font(.system(size: 11, weight: .bold))
                .tracking(1.5)
                .foregroundColor(SP.edgeGreen)
        case .passDay:
            Text("PASS\nDAY")
                .multilineTextAlignment(.center)
                .font(.system(size: 11, weight: .bold))
                .tracking(1.5)
                .foregroundColor(SP.amber)
        case .unavailable:
            Text("TAP TO\nOPEN")
                .multilineTextAlignment(.center)
                .font(.system(size: 11, weight: .bold))
                .tracking(1.5)
                .foregroundColor(SP.textSecondary)
        }
    }
}

// MARK: - Right pane (medium + top of large)

struct MatchupPane: View {
    let entry: WidgetEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            switch entry.status {
            case .qualifiedEdge:
                if let matchup = entry.topMatchup {
                    Text("MATCHUP")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(2.5)
                        .foregroundColor(SP.textSecondary)
                    Text(matchup)
                        .font(.system(size: 18, weight: .semibold, design: .serif))
                        .foregroundColor(SP.textPrimary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                }
                Spacer(minLength: 4)
                if let edge = entry.topEdgePct {
                    Text("EDGE")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(2.5)
                        .foregroundColor(SP.textSecondary)
                    Text(String(format: "+%.1f%%", edge))
                        .font(.system(size: 24, weight: .bold, design: .monospaced))
                        .foregroundColor(SP.edgeGreen)
                }
            case .passDay:
                Text("MARKET")
                    .font(.system(size: 9, weight: .bold))
                    .tracking(2.5)
                    .foregroundColor(SP.textSecondary)
                Spacer(minLength: 4)
                Text("Selective by design.")
                    .font(.system(size: 16, weight: .semibold, design: .serif))
                    .foregroundColor(SP.textPrimary)
                    .lineLimit(2)
            case .unavailable:
                Text("MARKET")
                    .font(.system(size: 9, weight: .bold))
                    .tracking(2.5)
                    .foregroundColor(SP.textSecondary)
                Spacer(minLength: 4)
                Text("Tap to open.")
                    .font(.system(size: 14))
                    .foregroundColor(SP.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(16)
    }
}

// MARK: - Concrete sizes

struct SmallView: View {
    let entry: WidgetEntry
    var body: some View {
        StatusSummary(entry: entry)
    }
}

struct MediumView: View {
    let entry: WidgetEntry
    var body: some View {
        HStack(spacing: 0) {
            StatusSummary(entry: entry)
            Rectangle()
                .fill(SP.textSecondary.opacity(SP.dividerOpacity))
                .frame(width: 1)
            MatchupPane(entry: entry)
        }
    }
}

struct LargeView: View {
    let entry: WidgetEntry
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                StatusSummary(entry: entry)
                Rectangle()
                    .fill(SP.textSecondary.opacity(SP.dividerOpacity))
                    .frame(width: 1)
                MatchupPane(entry: entry)
            }
            .frame(maxHeight: .infinity)

            Rectangle()
                .fill(SP.textSecondary.opacity(SP.dividerOpacity))
                .frame(height: 1)

            VStack(spacing: 10) {
                HStack(spacing: 10) {
                    proCell(label: "SIDE")
                    proCell(label: "LINE")
                }
                HStack(spacing: 10) {
                    proCell(label: "EDGE")
                    proCell(label: "SIZE")
                }
            }
            .padding(16)
            .frame(maxHeight: .infinity)
        }
    }

    @ViewBuilder
    private func proCell(label: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 9, weight: .bold))
                .tracking(2.5)
                .foregroundColor(SP.textSecondary)
            Text("[Pro]")
                .font(.system(size: 16, weight: .bold, design: .monospaced))
                .foregroundColor(SP.signalBlue)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(12)
        .background(SP.surface)
        .cornerRadius(8)
    }
}
