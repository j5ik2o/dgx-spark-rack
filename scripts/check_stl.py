"""バイナリSTLの閉じた形状、接続成分、体積、mm外形を確認する。"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import struct


def inspect(path):
    data=path.read_bytes()
    count=struct.unpack_from("<I",data,80)[0]
    assert len(data)==84+count*50,(path,"STLの長さ")
    vertices={}
    coordinates=[]
    edges=Counter()
    neighbors=defaultdict(set)
    volume=0.0
    degenerate=0
    for index in range(count):
        values=struct.unpack_from("<12fH",data,84+50*index)
        points=[values[i:i+3] for i in (3,6,9)]
        ids=[]
        for point in points:
            key=tuple(round(n,5) for n in point)
            if key not in vertices:
                vertices[key]=len(coordinates)
                coordinates.append(point)
            ids.append(vertices[key])
        if len(set(ids))<3:
            degenerate+=1
        for a,b in zip(ids,ids[1:]+ids[:1]):
            edges[tuple(sorted((a,b)))]+=1
            neighbors[a].add(b);neighbors[b].add(a)
        a,b,c=points
        volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    remaining=set(range(len(coordinates)))
    components=0
    while remaining:
        components+=1
        todo=[remaining.pop()]
        while todo:
            for other in neighbors[todo.pop()]:
                if other in remaining:
                    remaining.remove(other);todo.append(other)
    minimum=[min(p[i] for p in coordinates) for i in range(3)]
    maximum=[max(p[i] for p in coordinates) for i in range(3)]
    report={"triangles":count,"non_manifold_edges":sum(n!=2 for n in edges.values()),
            "degenerate_triangles":degenerate,"connected_components":components,
            "volume_mm3":volume,"minimum_mm":minimum,
            "dimensions_mm":[b-a for a,b in zip(minimum,maximum)]}
    assert report["non_manifold_edges"]==0,(path,report)
    assert degenerate==0 and components==1 and volume>0,(path,report)
    assert max(report["dimensions_mm"])<=230.001,(path,report)
    assert max(abs(n) for n in minimum)<0.00001,(path,report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    results={p.stem:inspect(p) for p in sorted(args.directory.glob("*.stl"))}
    assert results,"STLがありません"
    payload=json.dumps({"status":"passed","parts":results},ensure_ascii=False,indent=2)+"\n"
    if args.output:args.output.write_text(payload)
    print(json.dumps({"status":"passed","parts":len(results),
        "max_dimension_mm":max(max(r["dimensions_mm"]) for r in results.values())},ensure_ascii=False))


if __name__=="__main__":
    main()
