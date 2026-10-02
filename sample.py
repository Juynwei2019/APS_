from datetime import datetime, timedelta


def sample_data():
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    def at(days, hour):
        return (day + timedelta(days=days, hours=hour)).isoformat(timespec='minutes')
    return {
        'resources': [{'id': rid, 'name': name, 'windows': [{'start': at(d, 8), 'end': at(d, 17)} for d in range(5)]} for rid, name in [('CUT', '切割機'), ('ASM', '組裝站')]],
        'products': [{'id': 'P001', 'name': '標準零件', 'route': [{'name': '切割', 'resource': 'CUT', 'minutes_per_unit': 20}, {'name': '組裝', 'resource': 'ASM', 'minutes_per_unit': 30}]}],
        'orders': [{'id': 'WO001', 'product': 'P001', 'quantity': 10, 'priority': 1, 'due': at(0, 17)}, {'id': 'WO002', 'product': 'P001', 'quantity': 8, 'priority': 2, 'due': at(1, 17)}]
    }
