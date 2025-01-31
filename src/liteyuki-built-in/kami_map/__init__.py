from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from ...extraApi.base import Balance
from ...extraApi.rule import minimumCoin, NOT_BLOCKED, NOT_IGNORED, MODE_DETECT
from nonebot.rule import startswith
from .api import *
from .userData import *

pois_cmd = on_command(cmd="pois", aliases={"地点查询"},
                      rule=minimumCoin(2, "无法查询地点", startswith(("地点查询", "pois"))),
                      priority=12, block=True)

locate_ip = on_command(cmd="ip定位", aliases={"IP定位", "Ip定位", "iP定位"}, priority=12, block=True)


@pois_cmd.handle()
async def pois_handle(bot: Bot, event: Union[PrivateMessageEvent, GroupMessageEvent], state: T_State, args: Message = CommandArg()):
    args, params = Command.formatToCommand(str(args))
    keywords = Command.formatToString(*args)
    params["keywords"] = keywords
    if "page_size" not in params:
        params["page_size"] = 1
    pois = await get_poi(params=params)
    pois_list = pois["pois"]
    state["params"] = params
    if len(pois_list) > 0:
        state["city"] = True
        state["pois"] = pois
    else:
        bound_city = await ExtraData.getData(targetType=ExtraData.User, targetId=event.user_id, key="kami.map.cityname")
        if bound_city is None:
            reply = "你要查询哪个城市的%s呢" % keywords
            await pois_cmd.send(message=reply, at_sender=True)
        else:
            state["city"] = bound_city.split()[-1]


@pois_cmd.got(key="city")
async def pois_got_city(bot: Bot, event: Union[PrivateMessageEvent, GroupMessageEvent], state: T_State, args: Message = CommandArg()):
    if state["city"] is not True:
        state["params"]["region"] = str(state["city"])
        pois = await get_poi(params=state["params"])
    else:
        pois = state["pois"]
    pois_list = pois["pois"]
    if len(pois_list) > 0:
        replys = ""
        for poi in pois_list:
            if poi["cityname"] in ["重庆市", "北京市", "上海市", "天津市", "香港特别行政区", "澳门特别行政区"]:
                cityname = "%s %s" % (poi["cityname"], poi["adname"])
            else:
                cityname = "%s %s %s" % (poi["pname"], poi["cityname"], poi["adname"])
            reply = "%s\n" \
                    "- 地址: %s %s\n" \
                    "- 类型: %s\n" \
                    "- 坐标: %s\n" \
                    "- 地址码: %s\n\n" % (poi["name"], cityname, poi["address"], poi["type"], poi["location"], poi["adcode"])
            replys += reply
        replys += "数据来源于高德地图"
        at_sender = False
    else:
        replys = "什么都没有查到呢, 这是高德的锅, 不是我的锅"
        at_sender = True
    await pois_cmd.send(message=replys, at_sender=at_sender)
    await Balance.editCoinValue(user_id=event.user_id, delta=-2, reason="查询地点")


@locate_ip.handle()
async def ip_locate(bot: Bot, event: Union[PrivateMessageEvent, GroupMessageEvent], state: T_State, args: Message = CommandArg()):
    ip = str(args).strip()
    url = "https://restapi.amap.com/v3/ip?"
    params = {"key": await ExtraData.get_global_data(key="kami.map.key", default="")}
    if ip != "":
        params["ip"] = ip
    async with aiohttp.request("GET", url, ) as resp:
        data = await resp.json()
        if data["info"] == "OK":
            await locate_ip.send(message="- IP: %s\n- 地址: %s %s" % (ip, data["province"], data["city"]))
