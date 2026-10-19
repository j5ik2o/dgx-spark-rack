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
