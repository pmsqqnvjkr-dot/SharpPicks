//
//  Provider.swift
//  Timeline provider, response types, fetch + cache for the widget.
//

import Foundation
import WidgetKit

// MARK: - Backend response types
//
// Verified against https://app.sharppicks.ai/api/public/market-report
// on 2026-05-09. Only the fields the widget actually consumes are
// declared; everything else on the response is ignored to keep this
// resilient to backend additions. Optional throughout: the same
// endpoint returns {available: false, date: "..."} on dates with no
// model run.

struct MarketReport: Decodable {
    let available: Bool?
    let date: String?
    let market_efficiency_index: Int?
    let mei: MEI?
    let regime: String?
    let qualified_signals: Int?
    let games_analyzed: Int?
    let top_edge_pct: Double?
    let top_edge_team: String?
    let board: [BoardGame]?
}

struct MEI: Decodable {
    let current: Int?
}

struct BoardGame: Decodable {
    let away_team: String?
    let home_team: String?
    let edge: Double?
    let signal: Bool?
    let pick: String?
    let pick_label: String?
    let pick_side: String?
}

// MARK: - Widget entry

enum WidgetStatus: String, Codable {
    case qualifiedEdge
    case passDay
    case unavailable
}

struct WidgetEntry: TimelineEntry, Codable {
    let date: Date
    let status: WidgetStatus
    let mei: Int?
    let regime: String?
    let topMatchup: String?
    let topEdgePct: Double?
    // v1.1: large-widget bottom grid populated from public endpoint
    // (no Pro gate). topPickLabel mirrors what the SEO market report
    // already shows publicly. qualifiedCount + gamesAnalyzed feed the
    // SLATE cell ("1 of 6").
    let topPickLabel: String?
    let qualifiedCount: Int?
    let gamesAnalyzed: Int?
}

// MARK: - Provider

struct Provider: TimelineProvider {
    private static let endpoint = "https://app.sharppicks.ai/api/public/market-report"
    private static let refreshInterval: TimeInterval = 1800  // 30 minutes
    private static let cacheKey = "com.sharppicksllc.signals.widget.lastEntry"
    private static let requestTimeout: TimeInterval = 10

    // Realistic preview shown in the widget gallery and during transient
    // states. Apple uses this on first add and during reload windows.
    func placeholder(in context: Context) -> WidgetEntry {
        WidgetEntry(
            date: Date(),
            status: .qualifiedEdge,
            mei: 50,
            regime: "NORMAL",
            topMatchup: "Lakers @ Celtics",
            topEdgePct: 8.0,
            topPickLabel: "Lakers -3.5",
            qualifiedCount: 1,
            gamesAnalyzed: 6
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (WidgetEntry) -> Void) {
        if context.isPreview {
            completion(placeholder(in: context))
            return
        }
        Task {
            let entry = await fetchEntry()
            completion(entry)
        }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<WidgetEntry>) -> Void) {
        Task {
            let entry = await fetchEntry()
            let next = Date().addingTimeInterval(Self.refreshInterval)
            let timeline = Timeline(entries: [entry], policy: .after(next))
            completion(timeline)
        }
    }

    // MARK: Fetch

    private func fetchEntry() async -> WidgetEntry {
        guard let url = buildURL() else {
            return loadLastGood() ?? makeUnavailableEntry()
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = Self.requestTimeout
        request.cachePolicy = .reloadIgnoringLocalCacheData

        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            let report = try JSONDecoder().decode(MarketReport.self, from: data)
            let entry = entryFromReport(report)
            cacheLastGood(entry)
            return entry
        } catch {
            // Spec: never show error text on the widget surface. Fall
            // back to the last successful read, or a clean tap-to-open
            // placeholder if there is no cached state.
            return loadLastGood() ?? makeUnavailableEntry()
        }
    }

    private func buildURL() -> URL? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = TimeZone(identifier: "America/New_York")
        formatter.locale = Locale(identifier: "en_US_POSIX")
        let today = formatter.string(from: Date())

        var components = URLComponents(string: Self.endpoint)
        components?.queryItems = [
            URLQueryItem(name: "sport", value: "nba"),
            URLQueryItem(name: "date", value: today),
        ]
        return components?.url
    }

    private func entryFromReport(_ report: MarketReport) -> WidgetEntry {
        let qualifiedSignals = report.qualified_signals ?? 0
        let gamesAnalyzed = report.games_analyzed
        let mei = report.market_efficiency_index ?? report.mei?.current

        // Find the top signal by iterating the board and picking the
        // entry with signal=true and the highest edge.
        var topMatchup: String? = nil
        var topEdgePct: Double? = report.top_edge_pct
        var topPickLabel: String? = nil
        if let board = report.board {
            let signalGames = board.filter { $0.signal == true }
            if let top = signalGames.max(by: { ($0.edge ?? 0) < ($1.edge ?? 0) }) {
                if let away = top.away_team, let home = top.home_team {
                    topMatchup = "\(teamShort(away)) @ \(teamShort(home))"
                }
                if topEdgePct == nil { topEdgePct = top.edge }
                if let label = top.pick_label {
                    topPickLabel = shortenPickLabel(label)
                }
            }
        }

        let status: WidgetStatus
        if !(report.available ?? false) {
            status = .unavailable
        } else if qualifiedSignals > 0 {
            status = .qualifiedEdge
        } else {
            status = .passDay
        }

        return WidgetEntry(
            date: Date(),
            status: status,
            mei: mei,
            regime: report.regime,
            topMatchup: topMatchup,
            topEdgePct: topEdgePct,
            topPickLabel: topPickLabel,
            qualifiedCount: qualifiedSignals,
            gamesAnalyzed: gamesAnalyzed
        )
    }

    // "Detroit Pistons +4.5" -> "Pistons +4.5". The last token is the
    // line, the token before it is the team nickname. Compresses the
    // pick label so it fits in the large-widget cell at 16pt mono.
    private func shortenPickLabel(_ label: String) -> String {
        let parts = label.split(separator: " ").map(String.init)
        guard parts.count >= 2 else { return label }
        let line = parts.last ?? ""
        let teamWords = parts.dropLast()
        let lastTeamWord = teamWords.last ?? ""
        return "\(lastTeamWord) \(line)".trimmingCharacters(in: .whitespaces)
    }

    // Simple team-name short form: take the last word of the team
    // name. "Los Angeles Lakers" -> "Lakers". Avoids maintaining a
    // TLA mapping table while staying readable.
    private func teamShort(_ team: String) -> String {
        team.split(separator: " ").last.map(String.init) ?? team
    }

    private func makeUnavailableEntry() -> WidgetEntry {
        WidgetEntry(
            date: Date(),
            status: .unavailable,
            mei: nil,
            regime: nil,
            topMatchup: nil,
            topEdgePct: nil,
            topPickLabel: nil,
            qualifiedCount: nil,
            gamesAnalyzed: nil
        )
    }

    // MARK: Cache (UserDefaults, per-extension sandbox)
    //
    // v1 caches in the widget extension's own UserDefaults. Not shared
    // with the main app. v2 will migrate to UserDefaults(suiteName:)
    // backed by an App Group so the main app can pre-seed Pro auth
    // and recent state.

    private func cacheLastGood(_ entry: WidgetEntry) {
        do {
            let data = try JSONEncoder().encode(entry)
            UserDefaults.standard.set(data, forKey: Self.cacheKey)
        } catch {
            // best-effort
        }
    }

    private func loadLastGood() -> WidgetEntry? {
        guard let data = UserDefaults.standard.data(forKey: Self.cacheKey) else { return nil }
        return try? JSONDecoder().decode(WidgetEntry.self, from: data)
    }
}
