const TEAM_ABBR = {
  'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
  'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
  'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
  'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
  'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL',
  'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
  'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
  'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
  'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
  'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC',
  'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA',
  'Washington Wizards': 'WAS',
  'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
  'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
  'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
  'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
  'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
  'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
  'New York Yankees': 'NYY',
  'Oakland Athletics': 'OAK', 'Athletics': 'OAK', 'Sacramento Athletics': 'OAK',
  'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT',
  'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
  'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB',
  'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
};

export default function teamAbbr(name) {
  if (!name) return '???';
  if (TEAM_ABBR[name]) return TEAM_ABBR[name];
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[words.length - 1].substring(0, 2)).toUpperCase();
  return name.substring(0, 3).toUpperCase();
}

const TEAM_CITY = {
  'Atlanta Hawks': 'Atlanta', 'Boston Celtics': 'Boston', 'Brooklyn Nets': 'Brooklyn',
  'Charlotte Hornets': 'Charlotte', 'Chicago Bulls': 'Chicago', 'Cleveland Cavaliers': 'Cleveland',
  'Dallas Mavericks': 'Dallas', 'Denver Nuggets': 'Denver', 'Detroit Pistons': 'Detroit',
  'Golden State Warriors': 'Golden State', 'Houston Rockets': 'Houston', 'Indiana Pacers': 'Indiana',
  'LA Clippers': 'LA', 'Los Angeles Clippers': 'LA Clippers', 'Los Angeles Lakers': 'LA Lakers',
  'Memphis Grizzlies': 'Memphis', 'Miami Heat': 'Miami', 'Milwaukee Bucks': 'Milwaukee',
  'Minnesota Timberwolves': 'Minnesota', 'New Orleans Pelicans': 'New Orleans',
  'New York Knicks': 'New York', 'Oklahoma City Thunder': 'Oklahoma City',
  'Orlando Magic': 'Orlando', 'Philadelphia 76ers': 'Philadelphia', 'Phoenix Suns': 'Phoenix',
  'Portland Trail Blazers': 'Portland', 'Sacramento Kings': 'Sacramento',
  'San Antonio Spurs': 'San Antonio', 'Toronto Raptors': 'Toronto', 'Utah Jazz': 'Utah',
  'Washington Wizards': 'Washington',
  'Arizona Diamondbacks': 'Arizona', 'Atlanta Braves': 'Atlanta', 'Baltimore Orioles': 'Baltimore',
  'Boston Red Sox': 'Boston', 'Chicago Cubs': 'Chicago', 'Chicago White Sox': 'Chicago Sox',
  'Cincinnati Reds': 'Cincinnati', 'Cleveland Guardians': 'Cleveland', 'Colorado Rockies': 'Colorado',
  'Detroit Tigers': 'Detroit', 'Houston Astros': 'Houston', 'Kansas City Royals': 'Kansas City',
  'Los Angeles Angels': 'LA Angels', 'Los Angeles Dodgers': 'LA Dodgers', 'Miami Marlins': 'Miami',
  'Milwaukee Brewers': 'Milwaukee', 'Minnesota Twins': 'Minnesota', 'New York Mets': 'NY Mets',
  'New York Yankees': 'NY Yankees',
  'Oakland Athletics': 'Oakland', 'Athletics': 'Oakland', 'Sacramento Athletics': 'Sacramento',
  'Philadelphia Phillies': 'Philadelphia', 'Pittsburgh Pirates': 'Pittsburgh',
  'San Diego Padres': 'San Diego', 'San Francisco Giants': 'San Francisco',
  'Seattle Mariners': 'Seattle', 'St. Louis Cardinals': 'St. Louis', 'Tampa Bay Rays': 'Tampa Bay',
  'Texas Rangers': 'Texas', 'Toronto Blue Jays': 'Toronto', 'Washington Nationals': 'Washington',
};

export function teamCity(name) {
  if (!name) return '???';
  if (TEAM_CITY[name]) return TEAM_CITY[name];
  const words = name.trim().split(/\s+/);
  if (words.length <= 2) return words[0];
  return words.slice(0, -1).join(' ');
}
