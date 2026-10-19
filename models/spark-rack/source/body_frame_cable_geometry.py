"""配線予約を接線付きの管で描き、開放式の余長受けを作る。"""
import FreeCAD as App
import Part


def tube(route):
    edges = []
    for s in route['segments']:
        start, end = App.Vector(*s['start']), App.Vector(*s['end'])
        edges.append(Part.makeLine(start, end) if s['type'] == 'line'
                     else Part.Arc(start, App.Vector(*s['middle']), end).toShape())
    wire = Part.Wire(edges)
    tangent = edges[0].tangentAt(edges[0].FirstParameter)
    profile = Part.Wire([Part.makeCircle(route['diameter_mm'] / 2,
                                        App.Vector(*route['segments'][0]['start']), tangent)])
    return wire.makePipeShell([profile], True, False)


def create_cable_geometry(scene):
    from body_frame_geometry import block, item, COLORS
    data = scene['cable_management']
    parts, cables, storage = [], [], []
    for recipe in data['mounts']:
        shape = block(recipe['origin'], recipe['size'])
        if recipe.get('tie_plate'):
            x, y, z = recipe['origin']
            for height in (80, 96, 144, 160):
                shape = shape.cut(block([x - 1, y + 4, height], [6, 8, 3]))
        if recipe['slots']:
            x, y, z = recipe['origin']
            for dx in (8, 58):
                for dy in (30, 90, 150):
                    shape = shape.cut(block([x + dx, y + dy, z - 1], [8, 3, 6]))
            shape = shape.cut(block([recipe['feed_x'] - 12, recipe['feed_y'], z - 1], [24, 30, 6]))
        parts.append(item(recipe['name'], recipe['label'], shape.removeSplitter(), 'cable_mount'))
    for route in data['paths']:
        cables.append(item(route['name'], route['label'], tube(route), 'cable_' + route['family'],
                           endpoints=route['endpoints'], detachable_with=route.get('detachable_with')))
    for reservation in data['storage']:
        storage.append(item(reservation['name'], reservation['label'],
                            Part.makeTorus(reservation['radius'], reservation['diameter'] / 2,
                                           App.Vector(*reservation['center']), App.Vector(*reservation['normal'])),
                            'cable_storage', color=COLORS['cable_' + reservation['family']]))
    return parts, cables, storage
