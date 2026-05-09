//
//  SharpPicksWidget.swift
//  Home Screen widget for the SharpPicks: Signals iOS app.
//
//  Renders today's market signal status (qualified edge, pass day) on
//  three sizes. Pulls from the public market-report endpoint on the
//  same host as the Capacitor server.url. Refresh every 30 minutes.
//
//  v1 scope intentionally narrow:
//  - No App Group (Pro auth deferred to v2)
//  - No FINAL win/loss state (deferred to v2 alongside Pro auth)
//  - Large-widget Pro fields show [Pro] placeholders for everyone
//

import WidgetKit
import SwiftUI

@main
struct SharpPicksWidget: Widget {
    let kind: String = "SharpPicksWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            WidgetEntryView(entry: entry)
        }
        .configurationDisplayName("SharpPicks")
        .description("Today's market signal status.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}

struct WidgetEntryView: View {
    @Environment(\.widgetFamily) var family
    let entry: WidgetEntry

    var body: some View {
        Group {
            switch family {
            case .systemSmall:
                SmallView(entry: entry)
            case .systemMedium:
                MediumView(entry: entry)
            case .systemLarge:
                LargeView(entry: entry)
            default:
                SmallView(entry: entry)
            }
        }
        .widgetBg()
    }
}
