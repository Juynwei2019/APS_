"""Deterministic finite-capacity, non-preemptive scheduling."""
from datetime import datetime, timedelta


def timestamp(value):
    try:
        result = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError('時間格式錯誤') from None
    if result.tzinfo is not None:
        raise ValueError('請使用工廠當地時間，不含時區偏移')
    if result.second or result.microsecond:
        raise ValueError('時間精度為分鐘，請勿提供秒數')
    return result


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('資料必須是物件')
    for key in ('resources', 'products', 'orders'):
        if not isinstance(data.get(key), list):
            raise ValueError(f'{key} 必須是清單')
        ids = [item.get('id') for item in data[key] if isinstance(item, dict)]
        if len(ids) != len(data[key]) or any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(ids)) != len(ids):
            raise ValueError(f'{key} 識別碼必須唯一且非空')
        for item in data[key]:
            if 'name' in item and not isinstance(item['name'], str):
                raise ValueError('名稱必須是文字')
    resources = {r['id'] for r in data['resources']}
    for r in data['resources']:
        if not isinstance(r.get('windows'), list):
            raise ValueError('設備必須提供可用時段')
        if any(not isinstance(w, dict) or 'start' not in w or 'end' not in w for w in r['windows']):
            raise ValueError('可用時段必須包含開始與結束時間')
        previous = None
        for window in sorted(r['windows'], key=lambda w: timestamp(w['start'])):
            start, end = timestamp(window['start']), timestamp(window['end'])
            if start >= end or (previous and start < previous):
                raise ValueError('設備時段不得重疊，且結束必須晚於開始')
            previous = end
    products = {p['id'] for p in data['products']}
    for p in data['products']:
        if not isinstance(p.get('route'), list) or not p['route']:
            raise ValueError('產品必須包含至少一道工序')
        for op in p['route']:
            if not isinstance(op, dict) or ('name' in op and not isinstance(op['name'], str)):
                raise ValueError('工序格式錯誤')
            if op.get('resource') not in resources:
                raise ValueError('工序引用不存在的設備')
            minutes = op.get('minutes_per_unit')
            if type(minutes) is not int or not 1 <= minutes <= 100000:
                raise ValueError('單件加工分鐘必須是 1–100000 的整數')
    for order in data['orders']:
        if order.get('product') not in products:
            raise ValueError('訂單引用不存在的產品')
        if type(order.get('quantity')) is not int or not 1 <= order['quantity'] <= 100000:
            raise ValueError('訂單數量必須是 1–100000 的整數')
        if type(order.get('priority')) is not int or not 1 <= order['priority'] <= 9:
            raise ValueError('優先順序必須為 1–9（1 最高）')
        timestamp(order['due'])
    return data


def schedule(data, start, end, rule='priority'):
    validate(data)
    start, end = timestamp(start), timestamp(end)
    if start >= end:
        raise ValueError('排程結束必須晚於開始')
    if rule not in ('priority', 'due'):
        raise ValueError('未知排序規則')
    products = {p['id']: p for p in data['products']}
    calendars = {r['id']: sorted([(timestamp(w['start']), timestamp(w['end'])) for w in r['windows']]) for r in data['resources']}
    busy = {r: [] for r in calendars}
    operations, summaries = [], []
    key = (lambda o: (o['priority'], timestamp(o['due']), o['id'])) if rule == 'priority' else (lambda o: (timestamp(o['due']), o['priority'], o['id']))
    for order in sorted(data['orders'], key=key):
        ready, blocked = start, False
        for index, op in enumerate(products[order['product']]['route']):
            row = dict(order=order['id'], product=order['product'], operation=op.get('name', f'工序 {index+1}'), sequence=index+1, resource=op['resource'], duration=op['minutes_per_unit']*order['quantity'])
            duration = timedelta(minutes=row['duration'])
            slot = None
            if not blocked:
                for left, right in calendars[op['resource']]:
                    candidate, limit = max(left, ready, start), min(right, end)
                    for used_start, used_end in sorted(busy[op['resource']]):
                        if used_end <= candidate:
                            continue
                        if used_start >= candidate + duration:
                            break
                        candidate = max(candidate, used_end)
                    if candidate + duration <= limit:
                        slot = candidate
                        break
            if slot is None:
                row.update(status='unscheduled', reason='前置工序未排入' if blocked else '排程期間內無足夠連續可用產能')
                blocked = True
            else:
                ready = slot + duration
                busy[op['resource']].append((slot, ready))
                row.update(status='scheduled', start=slot.isoformat(timespec='minutes'), end=ready.isoformat(timespec='minutes'))
            operations.append(row)
        summaries.append(dict(order=order['id'], due=order['due'], completion=None if blocked else ready.isoformat(timespec='minutes'), status='unscheduled' if blocked else ('late' if ready > timestamp(order['due']) else 'on_time')))
    return dict(operations=operations, orders=summaries)
