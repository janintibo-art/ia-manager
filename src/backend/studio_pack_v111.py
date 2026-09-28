from src.backend import studio_advisor

def extend_packs_v111():
    if getattr(studio_advisor, '_v111_blender_extended', False):
        return
    enriched=[]
    for pack in studio_advisor.PACKS:
        record=dict(pack)
        tools=list(record.get('tools',()))
        if pack['id'] in ('3d','full') and 'blender' not in tools:
            tools.append('blender')
        record['tools']=tuple(tools)
        enriched.append(record)
    studio_advisor.PACKS=tuple(enriched)
    studio_advisor._v111_blender_extended=True
