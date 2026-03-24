from flask import Blueprint, jsonify, request, session
from models import db, Insight, Pick, User
from datetime import datetime
from zoneinfo import ZoneInfo
import re

insights_bp = Blueprint('insights', __name__)

ET = ZoneInfo('America/New_York')


def _visible_filter():
    now_et = datetime.now(ET).replace(tzinfo=None)
    return db.or_(
        Insight.status == 'published',
        db.and_(Insight.status == 'scheduled', Insight.publish_date <= now_et)
    )


def get_current_user():
    from app import get_current_user_obj
    return get_current_user_obj()


def insight_to_dict(insight):
    return {
        'id': insight.id,
        'title': insight.title,
        'slug': insight.slug,
        'category': insight.category,
        'excerpt': insight.excerpt,
        'content': insight.content,
        'status': insight.status,
        'publish_date': insight.publish_date.isoformat() if insight.publish_date else None,
        'featured': insight.featured,
        'pass_day': insight.pass_day,
        'reading_time_minutes': insight.reading_time_minutes,
        'related_pick_ids': insight.related_pick_ids or [],
        'date_range_start': insight.date_range_start,
        'date_range_end': insight.date_range_end,
        'story_type': getattr(insight, 'story_type', None),
        'has_related_picks': bool(insight.related_pick_ids) or bool(insight.date_range_start),
        'created_at': insight.created_at.isoformat() if insight.created_at else None,
    }


@insights_bp.route('', methods=['GET'])
@insights_bp.route('/', methods=['GET'])
def get_insights():
    category = request.args.get('category')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = Insight.query.filter(_visible_filter())

    if category and category != 'all':
        query = query.filter_by(category=category)

    query = query.order_by(Insight.publish_date.desc())
    total = query.count()
    insights = query.offset(offset).limit(limit).all()

    return jsonify({
        'insights': [insight_to_dict(i) for i in insights],
        'total': total,
        'has_more': offset + limit < total,
    })


@insights_bp.route('/latest', methods=['GET'])
def get_latest():
    pass_day_param = request.args.get('pass_day')

    if pass_day_param == 'true':
        insight = Insight.query.filter(
            _visible_filter(), Insight.pass_day == True
        ).order_by(Insight.publish_date.desc()).first()
        if insight:
            return jsonify(insight_to_dict(insight))

    insight = Insight.query.filter(
        _visible_filter()
    ).order_by(Insight.publish_date.desc()).first()

    if not insight:
        return jsonify({'error': 'No insights found'}), 404

    return jsonify(insight_to_dict(insight))


@insights_bp.route('/<insight_id>', methods=['GET'])
def get_insight(insight_id):
    insight = Insight.query.filter(
        _visible_filter(), Insight.id == insight_id
    ).first()
    if not insight:
        insight = Insight.query.filter(
            _visible_filter(), Insight.slug == insight_id
        ).first()
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404
    return jsonify(insight_to_dict(insight))


@insights_bp.route('/slug/<slug>', methods=['GET'])
def get_insight_by_slug(slug):
    insight = Insight.query.filter(
        _visible_filter(), Insight.slug == slug
    ).first()
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404
    return jsonify(insight_to_dict(insight))


@insights_bp.route('/<insight_id>/picks', methods=['GET'])
def get_related_picks(insight_id):
    """Return mini pick cards for a journal entry's related picks."""
    insight = Insight.query.filter(
        _visible_filter(), Insight.id == insight_id
    ).first()
    if not insight:
        insight = Insight.query.filter(
            _visible_filter(), Insight.slug == insight_id
        ).first()
    if not insight:
        return jsonify({'picks': []})

    picks = []
    if insight.related_pick_ids:
        picks = Pick.query.filter(Pick.id.in_(insight.related_pick_ids)).order_by(Pick.game_date).all()
    elif insight.date_range_start and insight.date_range_end:
        picks = Pick.query.filter(
            Pick.game_date >= insight.date_range_start,
            Pick.game_date <= insight.date_range_end
        ).order_by(Pick.game_date).all()

    result = []
    for p in picks:
        result.append({
            'id': p.id,
            'side': p.side,
            'line': p.line,
            'game_date': p.game_date,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'result': p.result,
            'profit_units': p.profit_units,
            'edge_pct': p.edge_pct,
        })

    wins = sum(1 for p in result if p['result'] == 'win')
    losses = sum(1 for p in result if p['result'] == 'loss')
    total_units = sum(p['profit_units'] or 0 for p in result)

    return jsonify({
        'picks': result,
        'summary': {
            'total': len(result),
            'wins': wins,
            'losses': losses,
            'units': round(total_units, 2),
        }
    })


@insights_bp.route('/admin', methods=['POST'])
def create_insight():
    user = get_current_user()
    if not user or not user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    slug = data.get('slug') or re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

    existing = Insight.query.filter_by(slug=slug).first()
    if existing:
        return jsonify({'error': 'Slug already exists'}), 400

    content_text = data.get('content', '')
    word_count = len(content_text.split())
    reading_time = max(1, round(word_count / 200))

    insight = Insight(
        title=title,
        slug=slug,
        category=data.get('category', 'philosophy'),
        excerpt=data.get('excerpt', ''),
        content=content_text,
        status=data.get('status', 'draft'),
        publish_date=datetime.now(ET).replace(tzinfo=None) if data.get('status') == 'published' else None,
        featured=data.get('featured', False),
        pass_day=data.get('pass_day', False),
        reading_time_minutes=data.get('reading_time_minutes', reading_time),
        related_pick_ids=data.get('related_pick_ids', []),
        date_range_start=data.get('date_range_start'),
        date_range_end=data.get('date_range_end'),
    )

    db.session.add(insight)
    db.session.commit()

    return jsonify({'success': True, 'insight': insight_to_dict(insight)}), 201


@insights_bp.route('/admin/<insight_id>', methods=['PATCH'])
def update_insight(insight_id):
    user = get_current_user()
    if not user or not user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    insight = db.session.get(Insight, insight_id)
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404

    data = request.json

    for field in ['title', 'slug', 'category', 'excerpt', 'content', 'status', 'featured', 'pass_day',
                   'reading_time_minutes', 'related_pick_ids', 'date_range_start', 'date_range_end']:
        if field in data:
            setattr(insight, field, data[field])

    if data.get('status') == 'published' and not insight.publish_date:
        insight.publish_date = datetime.now(ET).replace(tzinfo=None)

    db.session.commit()
    return jsonify({'success': True, 'insight': insight_to_dict(insight)})


@insights_bp.route('/admin/<insight_id>', methods=['DELETE'])
def delete_insight(insight_id):
    user = get_current_user()
    if not user or not user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    insight = db.session.get(Insight, insight_id)
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404

    db.session.delete(insight)
    db.session.commit()
    return jsonify({'success': True})
