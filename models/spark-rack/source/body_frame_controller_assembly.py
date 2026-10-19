"""同じケース6組に共通する、基板の投入と蓋の差し込み順を参考外形で検査する。"""
import FreeCAD as App
import Part

from body_frame_assembly import MotionCheck, outside_offset


def check_controller_assembly(model):
    from controller_mount import place
    case = model['scene']['controller_case_assembly']
    controller = next(e for e in model['scene']['equipment'] if e['kind']=='controller')
    source = {e['name']:e for e in model['references']}
    items = {'body':dict(shape=source[controller['name']+'_body']['shape']),
             'lid':dict(shape=source[controller['name']+'_lid']['shape'])}
    shift = App.Vector(*case['reference_shift'])
    pose = (controller['dock_origin'],controller['u'],controller['v'],controller['w'])
    electronics = set()
    for recipe in case['reference_boxes']:
        shape = Part.makeBox(*recipe['size'],App.Vector(*recipe['origin']))
        shape.translate(shift)
        items[recipe['name']] = dict(shape=place(shape,*pose))
        electronics.add(recipe['name'])
    knob = case['knob_reference']
    shape = Part.makeCylinder(knob['radius'],knob['height'],App.Vector(*knob['origin']))
    shape.translate(shift)
    items['knob'] = dict(shape=place(shape,*pose))
    electronics.add('knob')
    check = MotionCheck(items)
    board_start = outside_offset(electronics,{'body'},items,controller['w'])
    board_path = [board_start,[0,0,0]]
    hit = check.path(electronics,{'body'},board_path)
    if hit:
        raise ValueError('制御器の基板と上面部品をケースへ入れられません: '+str(hit))
    lid_start = outside_offset({'lid'},{'body'}|electronics,items,controller['w'])
    lid_path = [lid_start,[0,0,0]]
    hit = check.path({'lid'},{'body'}|electronics,lid_path)
    if hit:
        raise ValueError('制御器の基板を入れた後に蓋を差せません: '+str(hit))
    count=sum(e['kind']=='controller' for e in model['scene']['equipment'])
    return dict(status='passed', applies_to_cases=count,
                steps=['基板と上面の部品をケースへ入れる','基板押さえと一体の蓋を合わせる',
                       '完成したケースを受け台へ載せ、解除式結束バンド2本で留める'],
                checked_reference_envelopes=sorted(electronics),
                board_offsets=board_path,lid_offsets=lid_path,
                scope='同一形状のケースの基板・端子台・表示器・つまみ土台・つまみの参考外形。',
                not_verified=['基板裏面の部品配置と配線','結束バンドの通し方と解除レバーの操作'],
                physical_validation=False)
