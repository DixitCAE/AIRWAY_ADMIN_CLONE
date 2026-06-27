import math

def get_visual_block(coords_list):

    coords = [(w, lat, lon) for (w, c, lat, lon) in coords_list if lat is not None]

    if len(coords) < 2:
        return ""

    # ✅ USE FIRST AND LAST (TRUE ROUTE FLOW)
    start = coords[0]
    end = coords[-1]

    lat1, lon1 = start[1], start[2]
    lat2, lon2 = end[1], end[2]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    angle = math.degrees(math.atan2(dlat, dlon))

    angle_abs = abs(angle)

    # ✅ VERTICAL
    if angle_abs > 60:
        top = start if lat1 > lat2 else end
        bottom = end if lat1 > lat2 else start

        return f"""
        <div class="viz">
            <div class="label">{top[0]}</div>
            <div class="line-vertical"></div>
            <div class="label">{bottom[0]}</div>
        </div>
        """

    # ✅ HORIZONTAL
    elif angle_abs < 30:
        left = start if lon1 < lon2 else end
        right = end if lon1 < lon2 else start

        return f"""
        <div class="viz-horizontal">
            <div class="h-label left">{left[0]}</div>
            <div class="h-label right">{right[0]}</div>
            <div class="line-horizontal"></div>
        </div>
        """

    # ✅ DIAGONAL (SVG — PERFECT FIX)
    else:

        # normalize positions
        if lat1 > lat2:
            y1, y2 = 10, 90
        else:
            y1, y2 = 90, 10

        if lon1 < lon2:
            x1, x2 = 10, 90
        else:
            x1, x2 = 90, 10

        return f"""
        <div class="viz-svg">
            <div class="pt" style="left:{x1}%; top:{y1}%;">{start[0]}</div>
            <div class="pt" style="left:{x2}%; top:{y2}%;">{end[0]}</div>

            <svg width="100%" height="100%">
                <line x1="{x1}%" y1="{y1}%" x2="{x2}%" y2="{y2}%"
                      stroke="red" stroke-width="3"/>
            </svg>
        </div>
        """
