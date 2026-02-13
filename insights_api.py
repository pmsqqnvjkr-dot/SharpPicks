from flask import Blueprint, jsonify, request, session
from models import db, Insight, User
from datetime import datetime
import re

insights_bp = Blueprint('insights', __name__)


def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None


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
        'created_at': insight.created_at.isoformat() if insight.created_at else None,
    }


@insights_bp.route('', methods=['GET'])
@insights_bp.route('/', methods=['GET'])
def get_insights():
    category = request.args.get('category')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = Insight.query.filter_by(status='published')

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
        insight = Insight.query.filter_by(
            status='published', pass_day=True
        ).order_by(Insight.publish_date.desc()).first()
        if insight:
            return jsonify(insight_to_dict(insight))

    insight = Insight.query.filter_by(
        status='published'
    ).order_by(Insight.publish_date.desc()).first()

    if not insight:
        return jsonify({'error': 'No insights found'}), 404

    return jsonify(insight_to_dict(insight))


@insights_bp.route('/<insight_id>', methods=['GET'])
def get_insight(insight_id):
    insight = Insight.query.filter_by(id=insight_id, status='published').first()
    if not insight:
        insight = Insight.query.filter_by(slug=insight_id, status='published').first()
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404
    return jsonify(insight_to_dict(insight))


@insights_bp.route('/slug/<slug>', methods=['GET'])
def get_insight_by_slug(slug):
    insight = Insight.query.filter_by(slug=slug, status='published').first()
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404
    return jsonify(insight_to_dict(insight))


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
        publish_date=datetime.now() if data.get('status') == 'published' else None,
        featured=data.get('featured', False),
        pass_day=data.get('pass_day', False),
        reading_time_minutes=data.get('reading_time_minutes', reading_time),
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

    for field in ['title', 'slug', 'category', 'excerpt', 'content', 'status', 'featured', 'pass_day', 'reading_time_minutes']:
        if field in data:
            setattr(insight, field, data[field])

    if data.get('status') == 'published' and not insight.publish_date:
        insight.publish_date = datetime.now()

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
