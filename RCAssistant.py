import discord, random, grequests, asyncio, validators, config, youtube_api
from Base import BaseData, ClientCheck
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord.utils import get
from discord_components import DiscordComponents, Button, ButtonStyle, Select, SelectOption
from bs4 import BeautifulSoup as BS
from typing import Union

#----------------------------------------------------------------------------------------#

bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())
DiscordComponents(bot)
db = BaseData("BaseData.db")
pingUser = "<@134046599646019584>"
yt = youtube_api.YouTubeDataAPI(config.GOOGLE_YOUTUBE_DATA_API_KEY)

guildID = 916698103829110814

CategoryOrdersID = 919011671341670412

order_msg_id = 1019886124900036628

welcome_chn_id = 924310034639372338
orders_chn_id = 919009017475506207
admin_chn_id = 921739699201122354
support_chn_id = 919007630276558848
news_chn_id = 921533988374478858
roles_chn_id = 924310974545149993

response_chn_admin_id = 960123040589561956
response_chn_id = 919006097560436816

LIVE_NOW_CHN_ID = 1019877881586921513


#------------------------------------PARSER-----------------------------------------------#

def parseSite():
    headers = {
        "User-agent" : "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36 OPR/77.0.4054.298"    
    }
    url = "https://rcduostudio.com"
    r = grequests.map([grequests.get(url=url, headers=headers)])[0]
    answer = {"Mixing":{
            "Solo":{}, "Duo/Trio":{}, "Chorus":{}
        },"Instrumentals":{
            "Live":{}, "Electronic":{}, "Original Song":{}
        },"Tuning/Timing":{
            "Tuning":{}, "Timing":{}, "Artificial harms":{}, "Harms Guide":{}
        },"Producing":{
            "Vocal Production":{}
        }}
    try:
        soup = BS(r.text, "html.parser")
        cards = soup.find_all("article", class_="service__item")
        for card in cards:
            title = card.find("h3", class_="service__item-title").text.strip()
            disc = card.find("p", class_="service__item-text").text.strip()
            price = card.find("p", class_="service__item-price").text.strip()
            puth = "Mixing"
            for i in answer.keys():
                if title in answer[i].keys():
                    puth = i
                    break
            answer[puth][title] = {"disc" : disc, "Price" : price.replace('$ ', '')}
        print(answer)
        return answer
    except Exception as E:
        print(f"Error - {E}")
        return

def OnlyUpdatePrices():
    a = parseSite()
    for title in a.keys():
        for i in a[title].keys():
            ClientCheck.dictPrice[i] = int(a[title][i]['Price'])

def UpdatePrices():
    emojis = {"Mixing":"🎹","Instrumentals":"🎼","Tuning/Timing":"🎶","Producing":"🎤"}

    answer1 = ""
    a = parseSite()
    for title in a.keys():
        answer1+=f"**{emojis[title]} {title}**\n"
        for i in a[title].keys():
            ClientCheck.dictPrice[i] = int(a[title][i]['Price'])
            answer1 += f"**•** *{i}* : {a[title][i]['disc']} - **{a[title][i]['Price']} $** {'minimum price' if title == 'Instrumentals' else 'per track' if i in ['Tuning', 'Timing'] else ''}\n"
        answer1 += "\n"
    return answer1

def promoUpdater():
    for percent, StartPercent, Name, service in db.getsql("SELECT percent, FirstPercent, Name, TypeService FROM Promocodes"):
        numsUsed = len(db.getsql(f"SELECT user FROM UserPromo WHERE promocode = '{Name}' AND Category = '{service}'"))
        if percent - StartPercent < 25:
            match (numsUsed, percent - StartPercent):
                case (5 | 6 | 7 | 8 | 9, 0) | (10 | 11 | 12 | 13 | 14, 5) | (15, 10):
                    db.getsql(f"UPDATE Promocodes SET percent = {percent+5} WHERE Name = '{Name}' AND TypeService = '{service}'")

class Stream:
 
    def __init__(self, title, streamer, game, thumbnail_url):
        self.title = title
        self.streamer = streamer
        self.game = game
        self.thumbnail_url = thumbnail_url

def CheckLiveStreamYoutube(chnID : str):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={chnID}&type=video&eventType=live&key={config.GOOGLE_YOUTUBE_DATA_API_KEY}"
    headers = {
        "User-agent" : "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36 OPR/77.0.4054.298"    
    }
    try:
        req1 = grequests.map([grequests.get(url, headers=headers)])
        res = req1[0].json()
        if len(res.get("items")) > 0:
            data = res.get("items")[0].get("snippet")
            title = data['title']
            streamer = data['channelTitle']
            thumbnail_url = data['thumbnails']["high"]["url"]
            stream = Stream(title, streamer, None, thumbnail_url)
            return stream
    except Exception as e:
        print(f"EXPECT EXPECTION IN [ CheckLiveStreamYoutube ] - {str(e)}")
        return "ERROR"

def CheckLiveStreamTwitch(nickname : str) -> Union[Stream, str]:
    url = "https://api.twitch.tv/helix/streams?user_login=" + nickname
    HEADERS = {
        'Client-ID': config.TWITCH_CLIENT_ID,
        'Authorization': 'Bearer ' + config.TWITCH_SECRET_KEY
    }
    try:
        req1 = grequests.get(url, headers=HEADERS)
        req = grequests.map([req1])
        
        res = req[0].json()
        if len(res['data']) > 0: # the twitch channel is live
            data = res['data'][0]
            title = data['title']
            streamer = data['user_name']
            game = data['game_name']
            thumbnail_url = data['thumbnail_url']
            stream = Stream(title, streamer, game, thumbnail_url)
            return stream
        else:
            return "OFFLINE"
    except Exception as e:
        print(f"EXPECT EXPECTION IN [ CheckLiveStreamTwitch ] - {str(e)}")
        return "ERROR"

#------------------------------------FUNCTIONS-----------------------------------------------#

async def perms(member,channel, messageSender = False):
    perms = channel.overwrites_for(member)
    perms.send_messages = messageSender
    await channel.set_permissions(member, overwrite=perms)

async def responseClient(channel):
    bttnsNum = [str(i) for i in range(1, 6)]
    bttnsNum.append('skip')
    bttns = [Button(label=str(i)) for i in range(1, 6)]
    msg = await channel.send(embed=discord.Embed(title="Response", description="Rate the quality of service provision from 1 to 5", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), components=[bttns,[Button(style=ButtonStyle.blue,label="skip")]])
    try:
        ServiceProvision = await bot.wait_for("button_click", check=lambda i:i.component.label in bttnsNum and i.channel == channel, timeout=600)
    except asyncio.TimeoutError:
        await msg.delete()
        await channel.delete()
        return
    try:
        await ServiceProvision.respond()
    except Exception:
        pass
    chnl = bot.get_channel(response_chn_admin_id)
    usabComment = ""
    ServiceProvisionComment = ""

    if ServiceProvision.component.label == "skip":
        await msg.edit(embed=discord.Embed(title='Great', colour=discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"),components=[])
        await asyncio.sleep(600)
        try:
            await channel.delete()
        except Exception:
            pass
        return

    if ServiceProvision.component.label in ['3', '2', '1']:
        await msg.edit(embed=discord.Embed(description="What exactly did you not like?", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), components=[])
        await perms(bot.get_guild(guildID).get_member(ServiceProvision.author.id),channel , True)
        try:
            serviceComment = await bot.wait_for("message", check=lambda i:i.channel == channel and i.author != bot.user, timeout=600)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        await perms(bot.get_guild(guildID).get_member(ServiceProvision.author.id),channel , False)
        ServiceProvisionComment = serviceComment.content
        await serviceComment.delete()

    await msg.edit(embed=discord.Embed(title="Response", description="Rate the usability of the bot from 1 to 5", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), components=[bttns])
    try:
        usability = await bot.wait_for("button_click", check=lambda i:i.component.label in bttnsNum and i.channel == channel and i.author != bot.user, timeout=600)
    except asyncio.TimeoutError:
        await msg.delete()
        await channel.delete()
        return
    try:
        await ServiceProvision.respond()
    except Exception:
        pass
    if usability.component.label in ['3', '2', '1']:
        await msg.edit(embed=discord.Embed(description="What exactly did you not like?", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 15 min"), components=[])
        await perms(bot.get_guild(guildID).get_member(ServiceProvision.author.id),channel , True)
        try:
            usabilityComment = await bot.wait_for("message", check=lambda i:i.channel == channel, timeout=900)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        usabComment = usabilityComment.content
        await usabilityComment.delete()


    await msg.edit(embed=discord.Embed(title="Response", description="Leave your comment for future users", colour = discord.Color.blue(), ), components=[])
    await perms(bot.get_guild(guildID).get_member(ServiceProvision.author.id),channel , True)
    try:
        comment = await bot.wait_for("message", check=lambda i:i.channel == channel, timeout=600)
    except asyncio.TimeoutError:
        await msg.delete()
        await channel.delete()
        return
    await perms(bot.get_guild(guildID).get_member(ServiceProvision.author.id),channel , False)
    await msg.edit(embed=discord.Embed(title="Great", description="Thanks for the feedback\nHave a nice day)", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), components=[])
    await comment.delete()
    await chnl.send(embed=discord.Embed(title="Response", description=f"""
    **Client** : {ServiceProvision.author.mention}
    **Quality of service provision** : {ServiceProvision.component.label} {ServiceProvisionComment} 
    **Usability of the bot** : {usability.component.label} {usabComment} 
    **Comment** : {comment.content}
    """, colour = discord.Color.blue()).set_thumbnail(url=ServiceProvision.author.avatar_url))

    await bot.get_channel(response_chn_id).send(embed=discord.Embed(title="Response", description=f"""
    **Client** : {ServiceProvision.author.mention}
    **Quality of service provision** : {ServiceProvision.component.label}
    **Usability of the bot** : {usability.component.label}
    **Comment** : {comment.content}
    """, colour = discord.Color.blue()).set_thumbnail(url=ServiceProvision.author.avatar_url))
    db.getsql(f"UPDATE Clients SET IsResponsed = 1 WHERE user_id = {ServiceProvision.author.id}")
    await asyncio.sleep(7)
    await msg.delete()
    await asyncio.sleep(600)
    try:
        await channel.delete()
    except Exception:
        pass

async def all_orders(bttn):
    try:
        await bttn.respond()
    except Exception:
        pass
    msg = await bttn.channel.send(
        embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.blue()),
        components=[
            Select(
                placeholder="Select a service category",
                options = [
                    SelectOption(label="Mixing", value="Mixing"),
                    SelectOption(label="Instrumentals", value="Instrumentals"),
                    SelectOption(label="Tuning/Timing", value="Tuning/Timing"),
                    SelectOption(label="Producing", value="Producing")
                ]
            )
        ], 
    )
    a = ("Mixing", "Instrumentals", "Tuning/Timing", "Producing")
    resp = await bot.wait_for("select_option", check=lambda i: i.values[0] in a and i.channel == bttn.channel and bttn.author != bot.user)
    service = resp.values[0]
    try:
        await resp.respond()
    except Exception:
        pass
    desc = ""
    for user_id, url, isActive in db.getsql(f"SELECT user_id, url, isActive FROM ConfirmedOrders WHERE service = '{service}'"):
        desc += f"**Client** : <@{user_id}>\n**Status** : {'🟢 Active' if bool(isActive) else '🔘 Closed'}\n**Confirmed link** : {url}\n\n"
    await msg.edit(embed=discord.Embed(title=f"Service **{service.upper()}**",description=desc, colour=discord.Color.blue()),components=[])

async def all_codes(bttn):
    try:
        await bttn.respond()
    except Exception:
        pass
    msg = await bttn.channel.send(
        embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
        components=[
            Select(
                placeholder="Select a service category",
                options = [
                    SelectOption(label="Mixing", value="Mixing"),
                    SelectOption(label="Instrumentals", value="Instrumentals"),
                    SelectOption(label="Tuning/Timing", value="Tuning/Timing"),
                    SelectOption(label="Producing", value="Producing"),
                    SelectOption(label="All", value="all")
                ]
            )
        ], 
    )
    a = ("Mixing", "Instrumentals", "Tuning/Timing", "Producing", "all")
    resp = await bot.wait_for("select_option", check=lambda i: i.values[0] in a and i.channel == bttn.channel and bttn.author != bot.user)
    type_service = resp.values[0]
    try:
        await resp.respond()
    except Exception:
        pass
    codes = ""
    for name, percent, owner in db.getsql(f"SELECT Name, percent, Owner FROM Promocodes WHERE TypeService = '{type_service}'"): 
        nums = len(db.getsql(f"SELECT promocode FROM UserPromo WHERE promocode = '{name}'"))
        codes += f"**Promocode** : {name} / *{percent}*%  [ **{nums}** ] {f'- {owner}' if owner != None else ''}\n"
    await msg.edit(embed=discord.Embed(title=type_service,description=codes, colour=discord.Color.greyple()), components=[])

async def create_promo(ctx):
    try:
        await ctx.respond()
    except Exception:
        pass
    name : str
    percent : int
    type_service : str

    a = ("Mixing1", "Instrumentals1", "Tuning/Timing1", "Producing1", "all1")

    while True:

        msg = await ctx.channel.send(
        embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
        components=[
            Select(
                placeholder="Select a service category",
                options = [
                    SelectOption(label="Mixing", value="Mixing1"),
                    SelectOption(label="Instrumentals", value="Instrumentals1"),
                    SelectOption(label="Tuning/Timing", value="Tuning/Timing1"),
                    SelectOption(label="Producing", value="Producing1"),
                    SelectOption(label="All", value="all1")
                ]
            )
        ], #colour=discord.Color.blurple()
    ) 
        resp = await bot.wait_for("select_option", check=lambda i: i.values[0] in a and i.channel == ctx.channel and ctx.author != bot.user)
        type_service = resp.values[0].replace("1", "")

        try:
            await resp.respond()
        except Exception:
            pass
        percent = 0
        Owner = ""
        await msg.edit(embed=discord.Embed(title="Percent",description="select percentage of promo code", colour=discord.Color.blurple()), components=[])
        while True:
            try:
                percentMsg = await bot.wait_for("message", check=lambda i: (i.content).isdigit() and i.channel == ctx.channel and ctx.author != bot.user)
                percent = int(percentMsg.content)
                await percentMsg.delete()
                break
            except TypeError:
                await ctx.send(embed=discord.Embed(description="you did not enter a number", colour=discord.Color.red()))
                continue
        await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the promo code", colour=discord.Color.blurple()))
        name = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
        name1 = name.content
        await name.delete()
        
        await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the Owner of the promo code", colour=discord.Color.blurple()), components=[])
        owner = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
        Owner = owner.content
        await owner.delete()
        await msg.edit(
            embed=discord.Embed(title="Is correct?",description=f"Type service : {type_service}\nPromo Code : {name1}\nPercent : {percent}%\nOwner : {Owner}", colour=discord.Color.greyple()),
            components=[
                [Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id="button_yes"), Button(label="No", emoji="❌", custom_id="button_no")],
                [Button(style=ButtonStyle.red, label="Cancel")]
            ]
        )#------------------------WAIT-FOR-CLICK-BUTTON---------------------------#

        resp1 = await bot.wait_for("button_click")
        try:
            await resp1.respond()
        except Exception:
            pass
        if resp1.component.custom_id == "button_yes":
            db.getsql(f"INSERT INTO Promocodes(TypeService, percent, Name, Owner, FirstPercent) VALUES ('{type_service}', {percent}, '{name1}', '{Owner}', {percent})")
            await msg.edit(embed=discord.Embed(title="Great", colour=discord.Color.greyple()), components=[])
            await asyncio.sleep(5)
            await msg.delete()
            break
        elif resp1.component.custom_id == "button_no":
            try:
                await msg.delete()
            except Exception:
                pass
            continue
        await msg.delete()
        break

async def add_vtuber(ctx):
    try:
        await ctx.respond()
    except Exception:
        pass
    user : str
    promocode : str
    id_channel : str
    platform : str
    user_name : str

    while True:

        msg = await ctx.channel.send(embed=discord.Embed(title="Member",description="Enter the Member", colour=discord.Color.blurple()))
        GetUser = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user and len(i.mentions) > 0)
        user = GetUser.content
        member = GetUser.mentions[0]
        await GetUser.delete()

        await msg.edit(
        embed=discord.Embed(title="Platform",description="Select a Platform", colour=discord.Color.greyple()),
        components=[
            Select(
                placeholder="Select a service category",
                options = [
                    SelectOption(label="Twitch", value="TWITCH"),
                    SelectOption(label="Youtube", value="YOUTUBE")
                ]
            )
        ], #colour=discord.Color.blurple()
    ) 
        resp = await bot.wait_for("select_option", check=lambda i: i.values[0] in ("TWITCH","YOUTUBE") and i.channel == ctx.channel and ctx.author != bot.user)
        platform = resp.values[0]

        try:
            await resp.respond()
        except Exception:
            pass
        if platform == "YOUTUBE": 
            await msg.edit(embed=discord.Embed(title="Channel",description="Enter the channel user", colour=discord.Color.blurple()), components=[])
            id1 = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
            user_name = id1.content
            id_channel = yt.get_channel_id_from_user(id1.content)
            await id1.delete()
        elif platform == "TWITCH":
            await msg.edit(embed=discord.Embed(title="Streamer name", description="Enter the streamer name", colour=discord.Color.blurple()), components=[])
            user_name1 = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
            user_name = user_name1.content
            await user_name1.delete()

        await msg.edit(embed=discord.Embed(title="Promocode",description="Enter the promo code", colour=discord.Color.blurple()))
        promocode_msg = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
        promocode = promocode_msg.content
        await promocode_msg.delete()

        urlLive = f"https://www.twitch.tv/{user_name}" if platform == "TWITCH" else f"https://www.youtube.com/c/{user_name}"
        await msg.edit(
            embed=discord.Embed(title="Is correct?",description=f"Member : {user_name}\nPromocode : {promocode} (10%)\n[LINK TO {'CHANNEL' if platform == 'YOUTUBE' else 'STREAMER'}]({urlLive})", colour=discord.Color.greyple()),
            components=[
                [Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id="button_yes"), Button(label="No", emoji="❌", custom_id="button_no")],
                [Button(style=ButtonStyle.red, label="Cancel")]
            ]
        )#------------------------WAIT-FOR-CLICK-BUTTON---------------------------#

        resp1 = await bot.wait_for("button_click")
        try:
            await resp1.respond()
        except Exception:
            pass
        if resp1.component.custom_id == "button_yes":
            role = get(ctx.guild.roles, id=1019132409431719957)
            await member.add_roles(role)
            db.getsql(f"INSERT INTO LiveStreams({'id' if platform == 'YOUTUBE' else 'streamer'}, place, status) VALUES ('{id_channel if platform == 'YOUTUBE' else user_name}', '{platform}', 'OFFLINE')")
            db.getsql(f"INSERT INTO Promocodes VALUES ('all', 10, '{promocode}', '{user}', 10)")
            await msg.edit(embed=discord.Embed(title="Great", colour=discord.Color.greyple()), components=[])
            await asyncio.sleep(5)
            await msg.delete()
            break
        elif resp1.component.custom_id == "button_no":
            try:
                await msg.delete()
            except Exception:
                pass
            continue
        await msg.delete()
        break

async def edit_promo(ctx):
    try:
        await ctx.respond()
    except Exception:
        pass
    name : str
    percent : int
    type_service : str

    a = ("Mixing1", "Instrumentals1", "Tuning/Timing1", "Producing1")

    while True:

        msg = await ctx.channel.send(
        embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
        components=[
            Select(
                placeholder="Select a service category",
                options = [
                    SelectOption(label="Mixing", value="Mixing1"),
                    SelectOption(label="Instrumentals", value="Instrumentals1"),
                    SelectOption(label="Tuning/Timing", value="Tuning/Timing1"),
                    SelectOption(label="Producing", value="Producing1")
                ]
            )
        ], #colour=discord.Color.blurple()
    ) 
        resp = await bot.wait_for("select_option", check=lambda i: i.values[0] in a and i.channel == ctx.channel and ctx.author != bot.user)
        type_service = resp.values[0].replace("1", "")

        try:
            await resp.respond()
        except Exception:
            pass

        percent = 0
        newOwner = ""
        while True:
            await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the promo code", colour=discord.Color.blurple()), components=[])
            name = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
            name1 = name.content
            await name.delete()

            await msg.edit(embed=discord.Embed(title="Percent",description="select percentage of promo code", colour=discord.Color.blurple()), components=[])
            try:
                percentMsg = await bot.wait_for("message", check=lambda i: (i.content).isdigit() and i.channel == ctx.channel and ctx.author != bot.user)
                percent = int(percentMsg.content)
                await percentMsg.delete()
            except TypeError:
                await ctx.channel.send(embed=discord.Embed(description="you did not enter a number", colour=discord.Color.red()))
                continue
            await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the Owner of the promo code", colour=discord.Color.blurple()), components=[])
            owner = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
            newOwner = owner.content
            await owner.delete()
            break
        

        await msg.edit(
            embed=discord.Embed(title="Is correct?",description=f"Type service : {type_service}\nPromo Code : {name1}\nPercent : {percent}%\nOwner : {newOwner}", colour=discord.Color.greyple()),
            components=[
                [Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id="button_yes"), Button(label="No", emoji="❌", custom_id="button_no")],
                [Button(style=ButtonStyle.red, label="Cancel")]
            ]
        )#------------------------WAIT-FOR-CLICK-BUTTON---------------------------#

        resp1 = await bot.wait_for("button_click")
        try:
            await resp1.respond()
        except Exception:
            pass
        if resp1.component.custom_id == "button_yes":
            db.getsql(f"UPDATE Promocodes SET percent = {percent}, Owner = '{newOwner}' WHERE TypeService = '{type_service}' AND Name = '{name1}'")
            await msg.edit(embed=discord.Embed(title="Great", colour=discord.Color.greyple()), components=[])
            await asyncio.sleep(5)
            await msg.delete()
            break
        elif resp1.component.custom_id == "button_no":
            try:
                await msg.delete()
            except Exception:
                pass
            continue
        await msg.delete()
        break
    
async def edit_cashback(ctx): 
    try:
        await ctx.respond()
    except Exception:
        pass
    msg = await ctx.channel.send(embed=discord.Embed(title="Users cachback",description="Enter username", colour=discord.Color.teal()))
    resp = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
    user_id = str(resp.content)[2:-1:]
    try:
        await resp.delete()
    except Exception:
        pass
    if db.getsql(f"SELECT Scores FROM Clients WHERE user_id = {user_id}") == []:
        await msg.edit(embed=discord.Embed(title="Users cachback",description=f"Sorry, but <@{user_id}> is not a customer (and has not made any order)", colour=discord.Color.teal()))
        await asyncio.sleep(7)
        try:
            await msg.delete()
        except Exception:
            pass
        return
    newCashback = 0
    activeCashback = db.getsql(f"SELECT Scores FROM Clients WHERE user_id = {user_id}")[0][0]
        
    while True:
        await msg.edit(embed=discord.Embed(title="Cashback", description=f"Active Cashback - {activeCashback} $\nEnter the cashback", colour=discord.Color.teal()), components=[])
        newCashbackMsg = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
        newCashback = newCashbackMsg.content
        try:
            await newCashbackMsg.delete()
        except Exception:
            pass
        await msg.edit(
                embed=discord.Embed(title="Is correct?",description=f"Client : <@{user_id}>\n cashback : {newCashback} $", colour=discord.Color.teal()),
                components=[
                    [Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id="button_yes"), Button(label="No", emoji="❌", custom_id="button_no")],
                    [Button(style=ButtonStyle.red, label="Cancel")]
                ]
            )#------------------------WAIT-FOR-CLICK-BUTTON---------------------------#

        resp1 = await bot.wait_for("button_click")
        try:
            await resp1.respond()
        except Exception:
            pass
        if resp1.component.custom_id == "button_yes":
            await msg.edit(embed=discord.Embed(title="Great", colour=discord.Color.green()), components=[])
            db.getsql(f"UPDATE Clients SET Scores = {newCashback} WHERE user_id = {user_id}")
            try:
                user = await bot.fetch_user(user_id)
                await user.send(f"Your cashback has been changed. New balance: {newCashback}")
            except Exception as E:
                print(str(E))
            await asyncio.sleep(5)
            await msg.delete()
            break
        elif resp1.component.custom_id == "button_no":
            continue
        await msg.delete()
        break

async def delete_promo(ctx):
    try:
        await ctx.respond()
    except Exception:
        pass

    type_service : str

    a = ("Mixing1", "Instrumentals1", "Tuning/Timing1", "Producing1")

    while True:

        msg = await ctx.channel.send(
        embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
        components=[
            Select(
                placeholder="Select a service category",
                options = [
                    SelectOption(label="Mixing", value="Mixing1"),
                    SelectOption(label="Instrumentals", value="Instrumentals1"),
                    SelectOption(label="Tuning/Timing", value="Tuning/Timing1"),
                    SelectOption(label="Producing", value="Producing1")
                ]
            )
        ], #colour=discord.Color.blurple()
    ) 
        resp = await bot.wait_for("select_option", check=lambda i: i.values[0] in a and i.channel == ctx.channel and ctx.author != bot.user)
        type_service = resp.values[0].replace("1", "")

        try:
            await resp.respond()
        except Exception:
            pass

        await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the promo code", colour=discord.Color.blurple()), components=[])
        name = await bot.wait_for("message", check=lambda i:i.channel == ctx.channel and ctx.author != bot.user)
        name1 = name.content
        await name.delete()

        await msg.edit(
            embed=discord.Embed(title="Is correct?",description=f"Type service : {type_service}\nPromo Code : {name1}", colour=discord.Color.greyple()),
            components=[
                [Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id="button_yes"), Button(label="No", emoji="❌", custom_id="button_no")],
                [Button(style=ButtonStyle.red, label="Cancel")]
            ]
        )#------------------------WAIT-FOR-CLICK-BUTTON---------------------------#
        
        resp1 = await bot.wait_for("button_click")
        try:
            await resp1.respond()
        except Exception:
            pass
        if resp1.component.custom_id == "button_yes":
            db.getsql(f"DELETE FROM Promocodes WHERE TypeService = '{type_service}' AND Name = '{name1}'")
            await msg.edit(embed=discord.Embed(title="Great", colour=discord.Color.greyple()), components=[])
            await asyncio.sleep(5)
            await msg.delete()
            break
        elif resp1.component.custom_id == "button_no":
            await msg.edit(embed=discord.Embed(title="Try again", colour=discord.Color.greyple()), components=[])
            continue
        await msg.delete()
        break

async def send_order(bttn):
    try:
        await bttn.respond()
    except Exception:
        pass
    try:
        options = []
        nm = []
        for name, receipt_id, category1 in db.getsql("SELECT name, receipt_id, category FROM Orders LIMIT 25"):
            if receipt_id not in nm:
                options.append(SelectOption(label=name, value=receipt_id, description=f"Category : {category1}", emoji="👤"))
                nm.append(receipt_id)
        del nm
        msg1 = await bttn.channel.send(
            embed=discord.Embed(title="Client",description="Select a client", colour=discord.Color.greyple()),
            components=[
                Select(
                    placeholder="Select a client",
                    options = options
                )
            ])
        resp = await bot.wait_for("select_option", check=lambda i: i.channel == bttn.channel and bttn.author != bot.user)
        idChn = resp.values[0]
        try:
            await resp.respond()
        except Exception:
            pass
        client = db.getsql(f"SELECT name FROM Orders WHERE receipt_id = {idChn}")[0][0]
        idClient = db.getsql(f"SELECT user_id FROM Orders WHERE name = '{client}' and receipt_id = {idChn} LIMIT 1")[0][0]
        await msg1.edit(embed=discord.Embed(title="Send Files", description=f"Send files to <#{idChn}>", colour=discord.Color.blue()), components = [])
        files1 = await bot.wait_for("message", check=lambda i:i.channel == bttn.channel)
        
        chn = bot.get_channel(int(idChn))
        await chn.purge()
        message1 = "\n"
        if files1.content != "":
            message1 += files1.content
        try: 
            user = await bot.fetch_user(idClient)
            await user.send(embed=discord.Embed(title="Your order is ready!",colour=discord.Color.blue()))
        except Exception as E:
            print(f"Send order to DM error - {E}")

        await msg1.edit(embed=discord.Embed(title="Files has been sent", description="Files has been sent", colour=discord.Color.blue()))
            
        listFiles = [await file.to_file() for file in files1.attachments]
        try:
            await chn.send(f"<@{idClient}>",embed=discord.Embed(title="Your order is ready!", description=f"Files:{message1}", colour=discord.Color.blue()), files=listFiles, components=[
            Button(style=ButtonStyle.green,label="Approve the order"), Button(label="Enter edits")
        ])
        except Exception:
            await msg1.edit(embed=discord.Embed(description="Client channel Error", colour=discord.Color.red()))
            await asyncio.sleep(5)
            await msg1.delete()
            return
    
        await files1.delete()
        try:
            await msg1.delete()
        except Exception:
            pass
    except Exception as E:
        print(E.with_traceback(None))
        m = await bttn.channel.send(embed=discord.Embed(title="No orders", colour=discord.Color.red()))
        await asyncio.sleep(5)
        await m.delete()
        return

async def ask(bttn):
    questionChannel = bot.get_channel(support_chn_id) #         reviwes-terminal
    await bttn.respond(embed=discord.Embed(title="Channel", description=f"{questionChannel.mention}", colour=discord.Color.blue()))
    msg = await questionChannel.send(embed=discord.Embed(title="Ask something", description=f"{bttn.author.mention} Ask something\ntext must be no longer than 1000 characters", colour=discord.Color.blue()))
    try:
        question = await bot.wait_for("message", check=lambda i:i.channel == questionChannel and bttn.author != bot.user and len(i.content) <= 1000, timeout=6006)
    except asyncio.TimeoutError:
        await msg.edit(embed=discord.Embed(title="Time is up", description="", colour=discord.Color.red()))
        await asyncio.sleep(7)
        await msg.delete()
        return
    await msg.delete()
    await question.delete()
    msg = await bttn.author.send(embed=discord.Embed(title="Expect answers", description="Expect responses from server administrators", colour=discord.Color.blue()))
    channel = bot.get_channel(admin_chn_id)#                 admin-terminal
    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    msgQuestion = await channel.send(embed=discord.Embed(title="Question", description=f"**{bttn.author.mention} Asking**:\n{question.content}", colour=discord.Color.blurple()).set_footer(text=f"date : {date}"))
    db.getsql("INSERT INTO Questions(name, question, user_id, message_id, message_id_DM) VALUES ('{0}', '{1.content}', {1.author.id}, {2}, {3})".format(str(question.author), question, msgQuestion.id, msg.id))
    await asyncio.sleep(10)
    
async def ask1(bttn):
    msg = await bttn.author.send(embed=discord.Embed(title="Ask something", description=f"{bttn.author.mention} Ask something\ntext must be no longer than 1000 characters", colour=discord.Color.blue()))
    try:
        question = await bot.wait_for("message", check=lambda i:bttn.author != bot.user and i.author != bot.user and len(i.content) <= 1000, timeout=600)
    except asyncio.TimeoutError:
        await msg.edit(embed=discord.Embed(title="Time is up", description="", colour=discord.Color.red()))
        await asyncio.sleep(7)
        await msg.delete()
        return

    await msg.edit(embed=discord.Embed(title="Expect answers", description="Expect responses from server administrators", colour=discord.Color.blue()))
    channel = bot.get_channel(admin_chn_id)#                 admin-terminal
    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    msgQuestion = await channel.send(embed=discord.Embed(title="Question", description=f"**{bttn.author.mention} Asking**:\n{question.content}", colour=discord.Color.blurple()).set_footer(text=f"date : {date}"))
    db.getsql("INSERT INTO Questions(name, question, user_id, message_id) VALUES ('{0}', '{1.content}', {1.author.id}, {2})".format(str(question.author), question, msgQuestion.id))
    await asyncio.sleep(10)
    await msg.delete()

async def news(bttn):
    try:
        await bttn.respond()
    except Exception:
        pass
    channel = bot.get_channel(news_chn_id)    #    news channel
    msg = await bttn.channel.send(embed=discord.Embed(title="Headline", description="Enter the news headline", colour=discord.Color.blurple()))
    try:
        resp = await bot.wait_for("message", check=lambda i:i.channel == bttn.channel,timeout=60)
    except asyncio.TimeoutError:
        await msg.edit(embed=discord.Embed(title="Time is up", description="", colour=discord.Color.red()))
        await asyncio.sleep(7)
        await msg.delete()
        return
    title=resp.content
    await resp.delete()

    await msg.edit(embed=discord.Embed(title="Description", description="Enter the news description", colour=discord.Color.blurple()))
    try:
        resp1 = await bot.wait_for("message", check=lambda i:i.channel == bttn.channel, timeout=1800)
    except asyncio.TimeoutError:
        await msg.edit(embed=discord.Embed(title="Time is up",description="" ,colour=discord.Color.red()))
        await asyncio.sleep(7)
        await msg.delete()
        return
    description = resp1.content
    await resp1.delete()
    while True:
        await msg.edit(embed=discord.Embed(title="Image",description="Will you use image?" ,colour=discord.Color.red()), components=[
            [Button(style=ButtonStyle.green,label="Set"), Button(label="No")]
        ])
        embedNews = discord.Embed(title=title, description=description, colour=discord.Color.blurple())
        respImage = await bot.wait_for("button_click", check=lambda i:i.channel == bttn.channel, timeout=600)
        try:
            await respImage.respond()
        except Exception:
            pass
        if respImage.component.label == "Set":
            await msg.edit(embed=discord.Embed(title="Image",description="Set image" ,colour=discord.Color.blurple()), components=[])
            url = await bot.wait_for("message", check=lambda i:i.channel == bttn.channel, timeout=600)
            try:
                url1 = url.content if url.content != "" else url.attachments[0].url
            except Exception as E:
                print(f"EXCEPTION - {E}")
                continue
            embedNews.set_image(url=url1)
            await url.delete()

        await msg.edit(embed=embedNews,
            components=[
                [Button(style=ButtonStyle.green, label="Send"), Button(style=ButtonStyle.red, label="Delete")]
            ]
        )
        try:
            resp2 = await bot.wait_for("button_click", check=lambda i:i.channel == bttn.channel, timeout=60)
        except asyncio.TimeoutError:
            await msg.edit(embed=discord.Embed(title="Time is up", colour=discord.Color.blurple()))
            await asyncio.sleep(7)
            await msg.delete()
            return
        try:
            await resp2.respond()
        except Exception:
            pass
        if resp2.component.label == "Send":
            await channel.send("@everyone",embed=embedNews)
            await msg.edit(embed=discord.Embed(title="Great", description=f"The news was sent to channel {channel.mention}", colour=discord.Color.green()), components=[])
            await asyncio.sleep(5)
            await msg.delete()
            return
        elif resp2.component.label == "Delete":
            await msg.delete()
            return
        break

async def giveAnswer(bttn):
        try:
            await bttn.respond()
        except Exception:
            pass
        channel = bot.get_channel(admin_chn_id)#                 admin-terminal
        names = [name[0] for name in db.getsql("SELECT DISTINCT name FROM Questions LIMIT 25")]
        options = [SelectOption(label=name, value=name) for name in names]
        try:
            msg1 = await channel.send(
            embed=discord.Embed(title="User",description="Select a user", colour=discord.Color.greyple()),
            
            components=[
                Select(
                    placeholder="Select a user",
                    options = options
                    )
                ]
            )
        except Exception:
            msg = await bttn.channel.send(embed=discord.Embed(description="No further questions", colour=discord.Color.blurple()))
            await asyncio.sleep(10)
            await msg.delete()
            return
        resp = await bot.wait_for("select_option", check=lambda i:i.channel == bttn.channel and bttn.author != bot.user)
        name = resp.values[0]
        try:
            await resp.respond()
        except Exception:
            pass

        for msgID in db.getsql(f"SELECT message_id FROM Questions WHERE name = '{name}' AND message_id NOT NULL"):
            try:
                msgQues = await channel.fetch_message(msgID[0])
                db.getsql(f"UPDATE Questions SET message_id = NULL WHERE message_id = {msgID[0]}")
                await msgQues.delete()
            except Exception:
                pass
        
        messages = ""
        lastQuestion = ""
        for question, answer in db.getsql(f"SELECT question, answer FROM Questions WHERE name = '{name}'"):
            messages += f"\n\n**Question** :\n{question}\n\n**Answer** :\n{answer}"
            lastQuestion = question
        await msg1.edit(embed=discord.Embed(title="Answer",description=f"Give an answer to **{name}**\n**Message history** : {messages}", colour=discord.Color.greyple()), components=[])
        user = await bot.get_guild(guildID).fetch_member(db.getsql(f"SELECT user_id FROM Questions WHERE name = '{name}'")[0][0])
        a = await user.create_dm()
        DMmessage = await a.fetch_message(db.getsql(f"SELECT message_id_DM FROM Questions WHERE name = '{name}' AND message_id_DM NOT NULL")[0][0])
        
        answer = await bot.wait_for("message", check=lambda i:i.channel == channel and bttn.author != bot.user)
        db.getsql(f"UPDATE Questions SET answer = '{answer.content}' WHERE question = '{lastQuestion}' AND name = '{name}'")
        description = f"**To {name}** :"
        await answer.delete()
        for question, answer in db.getsql(f"SELECT question, answer FROM Questions WHERE name = '{name}'"):
            description += f"\n\n**Question** :\n{question}\n\n**Answer** :\n{answer}"
        await DMmessage.edit(embed=discord.Embed(title="Answer", description=description + '\n\nIs your question resolved?', colour=discord.Color.blurple()), components=[
            [Button(style=ButtonStyle.green, label="Yes", emoji="✅"), Button(label="No", emoji="❌")]
        ])
        await msg1.delete()
        try:
            isResolved = await bot.wait_for("button_click", check=lambda i:i.component.label in ["Yes", "No"] and str(i.author) == name and bttn.author != bot.user, timeout=86400)
        except asyncio.TimeoutError:
            await DMmessage.edit(components=[])
            db.getsql(f"DELETE FROM Questions WHERE name = '{name}'")
            return
        try:
            await isResolved.respond()
        except Exception:
            pass
        if isResolved.component.label == "Yes":
            await DMmessage.edit(components=[])
            db.getsql(f"DELETE FROM Questions WHERE name = '{name}'")
            msg2 = await bot.get_channel(admin_chn_id).send(embed=discord.Embed(title="Great",description=f"{name} accepted the answer The question is closed !", colour=discord.Color.green()))
            await asyncio.sleep(10)
            await msg2.delete()
        elif isResolved.component.label == "No":
            await ask1(isResolved)

async def shop(r):
    admin_channel = bot.get_channel(admin_chn_id)           # admin-terminal
    guild = bot.get_guild(guildID)
    category = get(guild.categories, id=CategoryOrdersID)
    bttnBack = Button(style=ButtonStyle.red, label="Back")
    colorCategory = None
    isCont = False

    categorys = {
        "Mixing" : ["Solo", "Duo/Trio", "Chorus"],
        "Instrumentals" : ["Live", "Electronic", "Original Song"],
        "Tuning/Timing" : ["Tuning", "Timing", "Artificial harms", "Harms Guide"],
        "Producing" : ["Vocal Production"]
    }

    while True:
        #-----------------------------------PRESS-BUY------------------------------------#
            #-------------------------------CREATE-CHANNEL--------------------------------#
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                guild.get_member(r.author.id): discord.PermissionOverwrite(read_messages=True)
            }
            now = datetime.now()
            date1 = now.strftime("%d%m%Y")
            db.OrderId = db.getsql("SELECT NumOrder FROM Info")[0][0] + 1
            db.getsql(f"UPDATE Info SET NumOrder = {db.OrderId}")
            channel = await guild.create_text_channel(f"{str(r.author).split('#')[0]}_{db.OrderId}_{date1}", overwrites=overwrites, category=category)

            await perms(guild.get_member(r.author.id), channel, False)

            await r.respond(embed=discord.Embed(title="Create an order", description=f"Your channel has been created {channel.mention}", colour=discord.Color.blue()))
            #------------------------------------------------------------------------------#
            while True:
                msg = await channel.send(r.author.mention,
                    embed=discord.Embed(title="Select a service category",description=f"Selecet a service category", colour=discord.Color.blue()),
                    components=[
                    [Button(label="Mixing"), Button(label="Instrumentals")],
                    [Button(label="Tuning/Timing"), Button(label="Producing")],
                    [Button(style=ButtonStyle.red, label="Cancel")]
                    ]
                )

                a = ["Mixing", "Instrumentals", "Tuning/Timing", "Producing", "Cancel"]
                try:
                    resp = await bot.wait_for("button_click", check=lambda i: i.component.label in a and i.channel == channel, timeout=600)
                except asyncio.TimeoutError:
                    await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                    await asyncio.sleep(10)
                    await channel.delete()
                    return
                try:
                    await resp.respond()
                except Exception:
                    pass
                match resp.component.label:
                    case "Mixing":
                        colorCategory = discord.Color.blue()
                    case "Instrumentals":
                        colorCategory = discord.Color.dark_purple()
                    case "Tuning/Timing":
                        colorCategory = discord.Color.dark_teal()
                    case "Producing":
                        colorCategory = discord.Color.greyple()

                client1 = ClientCheck(str(resp.author.mention))
                client1.service = resp.component.label
                client1.Additional_options = []
                client1.url1 = ""
                client1.url_org = ""
                client1.percent = 100

                if resp.component.label == "Cancel":
                    await msg.delete()
                    await channel.delete()
                    return
                components = [Button(label=bttn) for bttn in categorys[resp.component.label]]
                while True:
                    while True:
                        await msg.edit(
                                embed=discord.Embed(title="Type", description="Select type", colour=colorCategory),
                                components=[
                                    components, [bttnBack]
                                ]
                            )
                        try:
                            resp2 = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and (i.component.label in categorys[resp.component.label] or i.component.label == "Back") and client1.user == str(i.author.mention) and i.channel == channel, timeout=600)
                        except asyncio.TimeoutError:
                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                            await asyncio.sleep(10)
                            await channel.delete()
                            return
                        try:
                            await resp2.respond()
                        except Exception:
                            pass
                        if resp2.component.label == "Back":
                            await msg.delete()
                            isCont = True
                            break

                        client1.type_service = resp2.component.label
                        #---------------------------------------LINKS-----------------------------------------#
                        await perms(guild.get_member(r.author.id), channel, True)

                        if resp.component.label == "Mixing":
                            await msg.edit(embed=discord.Embed(title="Link to the tracks", description="Send a link to the tracks", colour=colorCategory), components=[])
                            try:
                                lnk = await bot.wait_for("message", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel and validators.url(i.content), timeout=600)
                            except asyncio.TimeoutError:
                                await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                await asyncio.sleep(10)
                                await channel.delete()
                                return
                            client1.url1 = lnk.content
                            await lnk.delete()
                        
                        await msg.edit(embed=discord.Embed(title="Link to the original video or reference", description="Send a link to the original video or reference", colour=colorCategory), components=[])
                        try:
                            lnk = await bot.wait_for("message", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel and validators.url(i.content), timeout=600)
                        except asyncio.TimeoutError:
                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                            await asyncio.sleep(10)
                            await channel.delete()
                            return
                        client1.url_org = lnk.content
                        await lnk.delete()

                        if resp.component.label != "Instrumentals" and resp2.component.label != "Harms Guide" and resp2.component.label != "Artificial harms" and resp.component.label != "Producing":
                            await msg.edit(embed=discord.Embed(title="Number of tracks in the project", description="Enter the number of tracks in the project", colour=colorCategory), components=[])
                            try:
                                numb = await bot.wait_for("message", check=lambda i:i.author.id != bot.user.id and (i.content).isdigit() and int(i.content) <= 1000 and client1.user == str(i.author.mention) and i.channel == channel, timeout=600)
                            except asyncio.TimeoutError:
                                await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                await asyncio.sleep(10)
                                await channel.delete()
                                return
                            client1.tracks = int(numb.content)
                            await numb.delete()

                        await channel.purge()

                            #--------------------------------ADDITIONAL-SERVICES-----------------------------------#
                        await perms(guild.get_member(r.author.id), channel, False)

                        try:
                            await resp2.respond()
                        except Exception:
                            pass
                        descr = ""
                        if client1.url1 != "":
                            descr += f"{client1.url1}\n"
                        if client1.url_org != "":
                            descr += f"{client1.url_org}\n"
                        if client1.tracks != 0:
                            descr += f"\nTracks : {client1.tracks}\n"
                        msg = await channel.send(embed=discord.Embed(title="Materials", description=descr, colour=colorCategory),
                            components=[
                                [Button(style=ButtonStyle.green,label="Continue"), bttnBack]
                            ]
                        )

                        try:
                            isContinue = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel, timeout=600)
                        except asyncio.TimeoutError:
                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                            await asyncio.sleep(10)
                            await channel.delete()
                            return

                        try:
                            await isContinue.respond()
                        except Exception:
                            pass 
                        if isContinue.component.label == "Back":
                            continue
                        break
                    if isCont:
                        break
                    while True:
                        if (resp.component.label == "Producing") or (resp.component.label != "Instrumentals" and resp2.component.label != "Harms Guide" and resp2.component.label != "Artificial harms"):
                            await msg.edit(
                                embed=discord.Embed(title="Great !", description="Do you want to choose additional services?", colour=colorCategory),
                                components=[
                                    [Button(style=ButtonStyle.green, label="Yes", emoji="✅"), Button(label="Continue")],
                                    bttnBack
                                ]
                            )
                        if resp.component.label == "Producing":
                            while True:
                                try:
                                    resp3 = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel, timeout=600)
                                except asyncio.TimeoutError:
                                    await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                    await asyncio.sleep(10)
                                    await channel.delete()
                                    return
                                try:
                                    await resp3.respond()
                                except Exception:
                                    pass
                                match resp3.component.label:
                                    case "Back":
                                        isCont = True
                                        break
                                    case "Reset":
                                        client1.Additional_options = []
                                        await msg.edit(
                                            embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                            components=[
                                                [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue")]
                                            ]
                                        )
                                        continue
                                    case "Continue" | "No":
                                        await msg.edit(embed=discord.Embed(title="Great !", colour=discord.Color.green()), components=[])
                                        break

                                    case "Choose more" | "Yes":
                                        await msg.edit(
                                            embed=discord.Embed(title="Additional services", colour=colorCategory),
                                            components=[
                                                [Button(label="Mixing"), Button(label="Instrumentals"), Button(label="Tuning/Timing")],[bttnBack]
                                            ]
                                        )
                                        try:
                                            resp4 = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel, timeout=600)
                                        except asyncio.TimeoutError:
                                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                            await asyncio.sleep(10)
                                            await channel.delete()
                                            return
                                        try:
                                            await resp4.respond()
                                        except Exception:
                                            pass
                                        if resp4.component.label == "Back":
                                            await msg.edit(
                                                embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                                components=[
                                                [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue"), Button(label="Reset")]
                                                ]
                                            )
                                            continue
                                        try:
                                            await msg.edit(
                                                embed=discord.Embed(title="Additional services", colour=colorCategory),
                                                components=[
                                                    [Button(label=bttn) for bttn in categorys[resp4.component.label] if bttn not in client1.Additional_options],
                                                    [bttnBack]
                                                ]
                                            )
                                        except Exception:
                                            await msg.edit(
                                                embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                                components=[
                                                    [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue"), Button(label="Reset")]
                                                ]
                                            )
                                            continue
                                        typeResp = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel)
                                        try:
                                            await typeResp.respond()
                                        except Exception:
                                            pass

                                        if typeResp.component.label == "Back":
                                            await msg.edit(
                                            embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                            components=[
                                                [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue"), Button(label="Reset")]
                                            ]
                                        )
                                            continue
                                        client1.Additional_options.append(typeResp.component.label)
                                        await msg.edit(
                                            embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                            components=[
                                                [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue"), Button(label="Reset")],
                                                bttnBack
                                            ]
                                        )
                                        continue
                            if isCont:
                                break

                        elif resp.component.label != "Instrumentals" and resp2.component.label != "Harms Guide" and resp2.component.label != "Artificial harms":
                            while True:
                                try:
                                    resp3 = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel, timeout=600)
                                except asyncio.TimeoutError:
                                    await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                    await asyncio.sleep(10)
                                    await channel.delete()
                                    return
                                try:
                                    await resp3.respond()
                                except Exception:
                                    pass
                                match resp3.component.label:
                                    case "Back":
                                        isCont = True
                                        break
                                    case "Reset":
                                        client1.Additional_options = []
                                        await msg.edit(
                                            embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                            components=[
                                                [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue")]
                                            ]
                                        )
                                        continue
                                    case "Continue" | "No":
                                        await msg.edit(embed=discord.Embed(title="Great !", colour=discord.Color.green()), components=[])
                                        break

                                    case "Choose more" | "Yes":
                                        await msg.edit(
                                            embed=discord.Embed(title="Additional services\nTuning/Timing", colour=colorCategory),
                                            components=[
                                                [Button(label=bttn) for bttn in categorys["Tuning/Timing"] if bttn not in client1.Additional_options and bttn != client1.type_service],
                                                [bttnBack]
                                            ]
                                        )
                                        try:
                                            resp4 = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel)
                                        except asyncio.TimeoutError:
                                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                            await asyncio.sleep(10)
                                            await channel.delete()
                                            return
                                        try:
                                            await resp4.respond()
                                        except Exception:
                                            pass
                                        if resp4.component.label == "Back":
                                            continue
                                        client1.Additional_options.append(resp4.component.label)
                                        await msg.edit(
                                            embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(client1.Additional_options)), colour=colorCategory),
                                            components=[
                                                [Button(style=ButtonStyle.green, label="Choose more"), Button(label="Continue"), Button(label="Reset")]
                                            ]
                                        )
                                        continue
                            if isCont:
                                isCont = False
                                continue
                    #---------------------------------------PROMO-CODE----------------------------------------#
                        await msg.edit(
                            embed=discord.Embed(title="Great !", description="will you use a promo code?", colour=colorCategory),
                            components=[
                                [Button(style=ButtonStyle.green, label="Use promo code"), Button(label="No, Thanks")],
                                bttnBack
                            ]
                        )
                        e = ["Use promo code", "No, Thanks", "Back"]
                        try:
                            resp5 = await bot.wait_for("button_click", check=lambda i:i.component.label in e and client1.user == str(i.author.mention) and i.component.label in e and i.channel == channel)
                        except asyncio.TimeoutError:
                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                            await asyncio.sleep(10)
                            await channel.delete()
                            return
                        try:
                            await resp5.respond()
                        except Exception:
                            pass
                        match resp5.component.label:
                            case "Back":
                                continue
                        
                            case "Use promo code":
                                await msg.edit(embed=discord.Embed(title="Promo Code",description='Enter your promo code\n*or enter "skip"', colour=colorCategory), components=[])
                                while True:
                                    await perms(guild.get_member(r.author.id), channel, True)

                                    try:
                                        promocode = await bot.wait_for("message", check=lambda i:client1.user == str(i.author.mention))
                                    except asyncio.TimeoutError:
                                        await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                        await asyncio.sleep(10)
                                        await channel.delete()
                                        return
                                    await perms(guild.get_member(r.author.id), channel, False)
                                    if promocode.content.lower() == "skip":
                                        await promocode.delete()
                                        break
                                    elif db.getsql(f"SELECT Owner FROM Promocodes WHERE Owner = '{str(promocode.author)}' AND Name = '{promocode.content}' AND TypeService IN ('{client1.service}', 'all')") != []:
                                        await msg.edit(embed=discord.Embed(title="Something went wrong",description='You cannot use your own promo code\nTry another promo code\nor enter "skip"', colour=discord.Color.dark_red()))
                                        await promocode.delete()
                                        continue
                                    elif db.getsql(f"SELECT user FROM UserPromo WHERE user = '{str(promocode.author)}' AND promocode = '{promocode.content}' AND Category = '{client1.service}'") != []:
                                        await msg.edit(embed=discord.Embed(title="Something went wrong",description='You have already used this promo code\nTry another promo code\nor enter "skip"', colour=discord.Color.dark_red()))
                                        await promocode.delete()
                                        continue
                                    elif db.getsql(f"SELECT percent FROM Promocodes WHERE Name = '{promocode.content}' AND TypeService IN ('{client1.service}', 'all')") == []:
                                        await msg.edit(embed=discord.Embed(title="Something went wrong",description='Incorrect promo code\nTry another promo code\nor enter "skip"', colour=discord.Color.dark_red()))
                                        await promocode.delete()
                                        continue
                                    percent = db.getsql(f"SELECT percent FROM Promocodes WHERE Name = '{promocode.content}' AND TypeService IN ('{client1.service}', 'all')")[0][0]
                                    client1.percent = percent
                                    client1.Used_promocode = promocode.content
                                    await promocode.delete()
                                    await msg.edit(embed=discord.Embed(title="Great",colour=colorCategory), components=[])

                                    break
                            case "No, Thanks":
                                await msg.edit(embed=discord.Embed(title="Great !",description="", colour=colorCategory), components=[])
                        break
                    if isCont:
                        isCont = False
                        continue
                    if client1.percent == 100 and db.getsql(f"SELECT Name FROM Promocodes WHERE Owner = '{str(resp5.author)}'") != []:
                        client1.percent = int(db.getsql(f"SELECT percent FROM Promocodes WHERE Owner = '{str(resp5.author)}'")[0][0])
                        #------------------------------------RECEIPT-CLIENT---------------------------------------#
                    if client1.service == "Instrumentals":
                        tracks = f"\n**Tracks** : {client1.tracks}" if client1.tracks != 0 else ''

                        materials = "\n".join([i for i in [client1.url1, client1.url_org] if i != ""])
                        priceMsg = await admin_channel.send(embed=discord.Embed(title="RECEIPT", description=f"""
                        {pingUser}
**Client** : {client1.user}
**Service** : {client1.service}
**Type** : {client1.type_service}
**Additional Options** : {" | ".join(client1.Additional_options)}
**Promo code** : {client1.Used_promocode} | {f'{client1.percent}' if client1.percent != 100 else ''}
**Material** : {materials} {tracks}
**Deadline** : 
**Price** : $""", colour=colorCategory))
        
                        msgExpect = await channel.send(embed=discord.Embed(title="Expect the price", description="Expect a price from the Administrator", colour=colorCategory))
                        msgPrice = await admin_channel.send(pingUser,embed=discord.Embed(title="Price", description="Enter the price", colour=colorCategory))
                        price = await bot.wait_for("message", check=lambda i:i.channel == admin_channel and (i.content).isdigit())
                        client1.price = int(price.content)
                        await price.delete()

                        deadlinemsg = await admin_channel.send(pingUser,embed=discord.Embed(title="Deadline", description="Enter the deadline", colour=colorCategory))
                        deadline = await bot.wait_for("message", check=lambda i:i.channel == admin_channel and (i.content).isdigit())
                        client1.deadline = int(deadline.content)
                        try:
                            await deadlinemsg.delete()
                            await msgPrice.delete()
                            await deadline.delete()
                            await priceMsg.delete()
                            await msgExpect.delete()
                        except Exception:
                            pass
                    print("test 1")
                    dl = client1.getDeadline()
                    print("test 2") + len(db.getsql("SELECT * FROM Orders")) if len(db.getsql("SELECT * FROM Orders")) > 1 else client1.getDeadline()
                    priceOrder = client1.getPrice()
                    print("test 3")

                    deadline1 = f'\n**Deadline** : {dl} days' if dl != 0 and resp.component.label != "Producing" else ''
                    tracks = f"\n**Tracks** : {client1.tracks}" if client1.tracks != 0 else ''
                    materials = "\n".join([i for i in [client1.url1, client1.url_org] if i != ""])
                    embedCl = discord.Embed(title="YOUR RECEIPT", description=f"""
**Client** : {client1.user}
**Service** : {client1.service}
**Type** : {client1.type_service}
**Additional Options** : {" | ".join(client1.Additional_options)}
**Promo code** : {client1.Used_promocode} | {f'{client1.percent}' if client1.percent != 100 else ''}
**Material** : {materials} {tracks} {deadline1}
**Price** : {priceOrder}$""", colour=colorCategory)
                    await msg.edit(
                        embed=embedCl, components=[]
                    )
                        #---------------------------------------PAYMENT-----------------------------------------#
                    
                    components = [[Button(style=ButtonStyle.blue,label="Wise.com", custom_id="Wise.com"), Button(style=ButtonStyle.blue,label="PayPal", custom_id="PayPal"), Button(style=ButtonStyle.red,label="Reset", custom_id="Reset")]]
                    paymentMsg = await channel.send(
                        embed=discord.Embed(title="Choose a payment method", colour=colorCategory),
                        components=components
                        )
                    while True:
                        if not client1.isUsedCashback and db.getsql(f"SELECT Scores FROM Clients WHERE user_ID = {resp5.author.id}") != []:
                            if db.getsql(f"SELECT Scores FROM Clients WHERE user_ID = {resp5.author.id}")[0][0] != 0:
                                components.append([Button(style=ButtonStyle.green, label="Use cashback", custom_id="Use cashback")])
                                await paymentMsg.edit(components=components)
                        if not client1.isSpeedUpDL and deadline1 != '':
                            components.append([Button(style=ButtonStyle.green,label="Speed up the deadline [+ 50% to the price]", custom_id="Speed up the deadline")])
                            await paymentMsg.edit(components=components)
                        
                        try:
                            respPay = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel, timeout=86400)
                        except asyncio.TimeoutError:
                            await channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                            await asyncio.sleep(10)
                            await channel.delete()
                            return
                        #---------------------------------------WISE.COM-----------------------------------------#
                        try:
                            await respPay.respond()
                        except Exception:
                            pass
                        match respPay.component.custom_id:
                            case "Speed up the deadline":
                                client1.isSpeedUpDL = True
                                components = [[Button(style=ButtonStyle.blue,label="Wise.com"), Button(style=ButtonStyle.blue,label="PayPal"), Button(style=ButtonStyle.red,label="Reset")]]
                                priceOrder = client1.getPrice() * 1.5
                                
                                tracks = f"\n**Tracks** : {client1.tracks}" if client1.tracks != 0 else ''
                                priceMsg = await admin_channel.send(embed=discord.Embed(title="RECEIPT", description=f"""
                                {pingUser}
**Client** : {client1.user}
**Service** : {client1.service}
**Type** : {client1.type_service}
**Additional Options** : {" | ".join(client1.Additional_options)}
**Promo code** : {client1.Used_promocode} | {f'{client1.percent}' if client1.percent != 100 else ''}
**Material** : {materials} {tracks}
**Deadline** {dl} *SET*: 
**Price** : {priceOrder}$""", colour=colorCategory))
                                await paymentMsg.edit(embed=discord.Embed(title="Deadline", description="wait the deadline", colour=colorCategory), components=[])
                                deadlinemsg = await admin_channel.send(pingUser,embed=discord.Embed(title="Deadline", description="Enter the deadline", colour=colorCategory))
                                deadline = await bot.wait_for("message", check=lambda i:i.channel == admin_channel and (i.content).isdigit())
                                dl = int(deadline.content)
                                try:
                                    await deadlinemsg.delete()
                                    await priceMsg.delete()
                                    await deadline.delete()
                                except Exception:
                                    pass
                                await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=colorCategory), components=components)
                                
                                deadline1 = f'\n**Deadline** : {dl} days' if dl != 0 and resp.component.label != "Producing" else ''
                                embedCl = discord.Embed(title="YOUR RECEIPT", description=f"""
**Client** : {client1.user}
**Service** : {client1.service}
**Type** : {client1.type_service}
**Additional Options** : {" | ".join(client1.Additional_options)}
**Promo code** : {client1.Used_promocode} | {f'{client1.percent}' if client1.percent != 100 else ''}
**Material** : {materials} {tracks} {deadline1}
**Price** : {priceOrder}$""", colour=colorCategory)
                                await msg.edit(
                                    embed=embedCl, components=[]
                                )
                                continue

                            case "Wise.com":
                                await paymentMsg.edit(embed=discord.Embed(title="Receiver", description="""
**Name**: Mala Svitlana
**Postal Code**: 51925
**Adress**: Ukraine, reg. Dnipropetrovska, city.Kamianske, street. Kostelna, build.8, fl.4
**E-mail**: rcduocovers@gmail.com
**IBAN**: UA533220010000026203311644991
USD->UAH
                                """,
                            url="https://wise.com",
                            colour=colorCategory), 
                            components=[[Button(style=ButtonStyle.green, label="Payment made", emoji="✅")],bttnBack]
                            )
                            #---------------------------------------PAY-PAL-----------------------------------------#
                            case "PayPal":
                                await paymentMsg.edit(
                                    embed=discord.Embed(title="PayPal",description="rcduocovers@gmail.com", colour=discord.Color.dark_blue()),
                                    components=[[Button(style=ButtonStyle.green, label="Payment made", emoji="✅")], bttnBack]
                                )

                            case "Use cashback":
                                cashback = db.getsql(f"SELECT Scores FROM Clients WHERE user_ID = {respPay.author.id}")[0][0]
                                client1.isUsedCashback = True
                                priceOrder *= 1-(cashback*0.01) if cashback <= 20 else 0.8
                                priceOrder = round(priceOrder,2)
                                cashback -= cashback if cashback <= 20 else 20
                                components = [[Button(style=ButtonStyle.blue,label="Wise.com", custom_id="Wise.com"), Button(style=ButtonStyle.blue,label="PayPal", custom_id="PayPal"), Button(style=ButtonStyle.red,label="Reset", custom_id="Reset")]]
                                await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=colorCategory), components=components)
                                embedCl = discord.Embed(title="YOUR RECEIPT", description=f"""
**Client** : {client1.user}
**Service** : {client1.service}
**Type** : {client1.type_service}
**Additional Options** : {" | ".join(client1.Additional_options)}
**Promo code** : {client1.Used_promocode} | {f'{client1.percent}' if client1.percent != 100 else ''}
**Material** : {materials} {tracks} {deadline1}
**Price** : {priceOrder}$""", colour=colorCategory)
                                await msg.edit(
                                    embed=embedCl, components=[]
                                )

                                continue
                            case "Reset":
                                try:
                                    await respPay.channel.purge()
                                    del client1
                                except Exception:
                                    pass
                                isCont = True
                                break
                        confirm = await bot.wait_for("button_click", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel)
                        #---------------------------------------CONFIRM-----------------------------------------#
                        try:
                            await confirm.respond()
                        except Exception:
                            pass
                        if confirm.component.label == "Payment made":
                            await paymentMsg.edit(embed=discord.Embed(title="Screenshot or payment confirmation link",description='Send a screenshot or payment confirmation link',colour=colorCategory).set_footer(text='or type "back" to return to the payment method menu'), components=[])
                            while True:
                                await perms(guild.get_member(r.author.id), channel, True)
                                response1 = await bot.wait_for("message", check=lambda i:i.author.id != bot.user.id and client1.user == str(i.author.mention) and i.channel == channel and (i.content).isdigit() == False)
                                bttns = [Button(style=ButtonStyle.green,label="Confirm", emoji="✅"), Button(style=ButtonStyle.red,label="Invalid link"), Button(label="Remove the order", emoji="❌")]
                                await perms(guild.get_member(r.author.id), channel, False)
                                
                                if response1.content.lower() == "back":
                                    try:
                                        await response1.delete()
                                    except Exception:
                                        pass
                                    components = [[Button(style=ButtonStyle.blue,label="Wise.com", custom_id="Wise.com"), Button(style=ButtonStyle.blue,label="PayPal", custom_id="PayPal"), Button(style=ButtonStyle.red,label="Reset", custom_id="Reset")]]
                                    await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=colorCategory), components=components)
                                    isCont = True
                                    break

                                try:
                                    f = await response1.attachments[0].to_file()
                                    msg = await admin_channel.send(file=f,content=pingUser, embed=embedCl,
                                        components=[bttns]
                                    )
                                    confirUrl = str(response1.attachments[0].url)
                                except IndexError:
                                    msg = await admin_channel.send(content=f"{pingUser}\n{response1.content}",embed=embedCl, 
                                            components=[bttns]
                                    )
                                    confirUrl = response1.content
                                finally:
                                    try:
                                        await response1.delete()
                                    except Exception:
                                        pass
                                    await paymentMsg.edit(embed=discord.Embed(title="Wait for confirmation",description="Expect confirmation from administrators within 24 hours", colour=colorCategory), components=[])
                                c = ["Confirm", "Invalid link", "Remove the order"]
                                respC = await bot.wait_for("button_click", check=lambda i: i.component.label in c and i.message.id == msg.id, timeout=86400)
                                try:
                                    await respC.respond()
                                except Exception:
                                    pass
                                match respC.component.label:
                                    case "Confirm":
                                        dateOrder = str(datetime.now().strptime(str(datetime.now().strftime("%m/%d/%Y")),"%m/%d/%Y") + timedelta(days=dl)).replace("-", ".")
                                        await channel.purge()
                                        await channel.send(confirm.author.mention,embed=discord.Embed(title="Confirmed", description="Your order has been confirmed", colour=discord.Color.green()).set_footer(text=f"date : {dateOrder.replace('00:00:00', '')}"), components=[])                    
                                        
                                        scores2 = db.getsql(f"SELECT Scores FROM Clients WHERE user_id = {confirm.author.id}")
                                        scores = scores2[0][0] if scores2 != [] else 0

                                        if client1.isUsedCashback:
                                            db.getsql(f"UPDATE Clients SET Scores = {cashback} WHERE user_id = {respPay.author.id}")

                                        elif not client1.isUsedCashback:
                                            try:
                                                await confirm.author.send(f"Thank you for the order.  You have been awarded - {round(priceOrder*0.02, 2)} RC\nNew Balance : {scores + round(priceOrder*0.02, 2)}")
                                            except Exception:
                                                pass
                                        
                                        try:
                                            role = get(guild.roles, id=924322390438199306)
                                            role1 = get(guild.roles,id=924322816503971850)
                                            members = await bot.get_guild(guildID).fetch_member(confirm.author.id)
                                            lenID = len(db.getsql(f"SELECT Orders FROM Clients WHERE user_id = {confirm.author.id}"))
                                        except Exception:
                                            pass
                                        id = 0
                                        if lenID <= 0:
                                            db.getsql(f"INSERT INTO Clients VALUES({confirm.author.id}, 1, {scores + round(priceOrder*0.02, 2) if not client1.isUsedCashback else scores}, 0)")
                                        else:
                                            db.getsql(f"UPDATE Clients SET Scores = {scores + round(priceOrder*0.02, 2)} WHERE user_id = {confirm.author.id}")
                                            id = db.getsql(f"SELECT Orders FROM Clients WHERE user_id = {confirm.author.id}")[0][0]
                                        if id >= 3:
                                            try:
                                                await members.add_roles(role1)
                                            except Exception:
                                                pass
                                            db.getsql(f"UPDATE Clients SET Orders={id+1} WHERE user_id = {confirm.author.id}")
                                        
                                        elif id < 4:
                                            db.getsql(f"UPDATE Clients SET Orders={id+1} WHERE user_id = {confirm.author.id}")
                                            try:
                                                await members.add_roles(role)
                                            except Exception:
                                                pass

                                        db.getsql(f"INSERT INTO ConfirmedOrders VALUES ('{confirUrl}', '{client1.service}', '{str(confirm.author)}', 1,{confirm.author.id}, {channel.id})")                               
                                        if client1.percent != 100 : db.getsql(f"INSERT INTO UserPromo VALUES('{str(confirm.author)}', '{client1.Used_promocode}','{client1.service}')")
                                        db.getsql(f"INSERT INTO Orders VALUES({confirm.author.id}, {0}, '{str(confirm.author)}', '{client1.service}', {channel.id})")

                                        await msg.delete()
                                        promoUpdater()
                                        del msg
                                        return
                                    case "Invalid link":
                                        await channel.purge()
                                        await msg.delete()
                                        del msg
                                        paymentMsg = await channel.send(confirm.author.mention, embed=discord.Embed(title="Invalid link", description="Enter the correct link", colour=discord.Color.red()), components=[])
                                        continue
                                    case "Remove the order":
                                        await channel.purge()
                                        await msg.delete()
                                        
                                        await channel.send(confirm.author.mention, embed=discord.Embed(description="The order has been removed", colour=discord.Color.red()), components=[])
                                        await asyncio.sleep(5)
                                        try:
                                            await channel.delete()
                                            client1.reset()
                                            del client1
                                        except Exception:
                                            pass
                                return
                        if isCont:
                            isCont = False
                            continue
                        elif confirm.component.label == "Back":
                            components = [[Button(style=ButtonStyle.blue,label="Wise.com", custom_id="Wise.com"), Button(style=ButtonStyle.blue,label="PayPal", custom_id="PayPal"), Button(style=ButtonStyle.red,label="Reset", custom_id="Reset")]]
                            await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=colorCategory), components=components)
                            continue
                        break
                    break
                if isCont:
                    isCont = False
                    continue
                            
#---------------------------------EVENTS_FUNCTIONS--------------------------------------#

@bot.event
async def on_member_join(member):
    welcome_ch = bot.get_channel(welcome_chn_id)     # welcome channel                  # general chat
    embed = discord.Embed(title="WELCOME", description=f"""
        WELCOME TO **{bot.get_guild(guildID).name}** SERVER
        {member.mention}

        <#919009200682721300> - Information of the SERVER
        <#921533988374478858> - News of the SERVER
        <#924310974545149993> - Roles of the SERVER

    """, colour=discord.Color.magenta())
    embed.set_thumbnail(url=member.avatar_url)
    embed.set_image(url=(db.animeGifs[random.randint(0, len(db.animeGifs) - 1)]))
    await welcome_ch.send(embed=embed)

@bot.event
async def on_member_remove(member):
    welcome_ch = bot.get_channel(welcome_chn_id)     # welcome channel
    embed = discord.Embed(description=f"""
{str(member)} LEFT US
we will miss you !
    """, colour=discord.Color.dark_red())
    embed.set_image(url=(db.animeGifsBye[random.randint(0, len(db.animeGifsBye) - 1)]))
    await welcome_ch.send(embed=embed)
    

@bot.event
async def on_ready():
    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print(f"[ {date} ] Bot is connected [ {bot.user} ]")
    checkLiveStreamsTwitch.start()
    checkLiveStreamsYouTube.start()
    
    #--------------------------#
    #adminCHn = bot.get_channel(admin_chn_id)
    #await adminCHn.purge()
    #await adminCHn.send(embed=discord.Embed(title="Admin Panel", colour=discord.Color.blurple()),components=[
    #    [Button(style=ButtonStyle.green,label="Send Order"), Button(style=ButtonStyle.green,label="Give an answer")],
    #    [Button(style=ButtonStyle.blue,label="Create promo"),
    #    Button(label="Edit promo"),
    #    Button(label="Delete promo")],[Button(label="Show all promo codes"), Button(label="Edit cashback"), Button(style=ButtonStyle.blue,label="Add vtuber")],[Button(label="Send News")],
    #    Button(label="Show all confirmed orders")
    #])

    # create-an-order channel
    #orderChn = bot.get_channel(orders_chn_id)
    #await orderChn.purge()
    #await orderChn.send(embed=discord.Embed(title="Menu",description=answer1, colour=discord.Color.blue()),
    #    components=[
    #        [Button(style=ButtonStyle.green,label="Create an order", emoji="🛒"), Button(style=ButtonStyle.gray, label="Ask question", emoji="❔"), Button(style=ButtonStyle.blue, label="My cashback", emoji="💰"), Button(style=ButtonStyle.blue, label="About cashback", emoji="ℹ️")]
    #    ]
    #)

#    gender = discord.Embed(title="Gender",description="""
#    ♂️ - @Guy
#    ♀️ - @Girl""" ,colour=discord.Color.blue())
#    age = discord.Embed(title="Age", description="""
#    🌑 - @13-15
#    🌘 - @16-18
#    🌗 - @19-21
#    🌕 - @21+""", colour=discord.Color.blue())
#    occupation = discord.Embed(title="Occupation",description="""
#    🎤 - @Vocalist
#    🎶 - @Mixer
#    🎸 - @Instrumentalist
#    📣 - @Producer
#    ✏️ - @Animator
#    🖌 - @Artist""", colour=discord.Color.blue())
#    
#    await channel.send(embed=gender, components=[
#        [Button(label="♂️", custom_id="Gender1"), Button(label="♀️", custom_id="Gender2"), Button(label="Hide Gender", custom_id="Gender3")]
#    ])
#    await channel.send(embed=age, components=[
#        [Button(label="🌑", custom_id="Age1"),Button(label="🌘", custom_id="Age2"),Button(label="🌗", custom_id="Age3"),Button(label="🌕", custom_id="Age4"), Button(label="Hide Age", custom_id="Age5")]
#    ])
#    await channel.send(embed=occupation, components=[
#        [Button(label="🎤", custom_id="Occupation1"),Button(label="🎶", custom_id="Occupation2"),Button(label="🎸", custom_id="Occupation3")],
#        [Button(label="📣", custom_id="Occupation4"),Button(label="✏️", custom_id="Occupation5"),Button(label="🖌", custom_id="Occupation6")]
#        ]
#    )

@bot.event
async def on_button_click(bttn):
    match bttn.component.label:
        case "Create an order":
        #    try:
            await shop(bttn)
            #except Exception as e:
            #    print(f"bttn ERROR [SHOP] - {e.with_traceback(None)}")
        case "Ask question":
            try:
                await ask(bttn)
            except Exception as e:
                print(f"bttn ERROR [ASK] - {e}")
        case "My cashback":
            try:
                if db.getsql(f"SELECT Scores FROM Clients WHERE user_id = {bttn.author.id}") != []:
                    cachback = db.getsql(f"SELECT Scores FROM Clients WHERE user_id = {bttn.author.id}")[0][0]
                    await bttn.respond(embed=discord.Embed(title="Your Cashback", description=f"Balance - **{cachback}** RC", colour=discord.Color.blue()))
                else:
                    await bttn.respond(embed=discord.Embed(title="Your Cashback", description=f"In order to receive cashback, you must make at least 1 order", colour=discord.Color.blue()))
            except Exception as e:
                print(f"bttn ERROR [MY CACHBACK] - {e}")
        case "About cashback":
            try:
                embed = discord.Embed(title="About Cashback", description="""
What is cashback?
When you buy something, you get 2% of the amount of your order to your cashback balance. This means that cashback is a way to reduce the price of future orders.
After confirming the order, you will be credited with points in the form of RC currency (2% of the payment amount), in the future you will be able to use your RC in the order as a cashback to reduce its price.
1 **RC** = 1 **$**
cashback can only be used once per order (no more than 20% of the total amount of the order, and after using the cashback, N points will be deducted from your balance
""", colour=discord.Color.blue())
                embed.set_image(url="https://lh3.googleusercontent.com/fife/AAbDypCOySy6EFqL-ZfJ9TOM2rPcTuim7V0Q_mSBYpFJj8N0zoBSeJsGMP4oAB6E1xpbdd3jTOz0yt-EHCgqd-69LUO59DuRnKd6bbEE6VByKJRm8GyBWChArAnFtc8zYyoTzvt99G_YJQgV2M-GSyds12sLma3C3RNGXzSCmntsGZkHFP-50m7_SEx3GCm4IFlUBWFed7s9gTcwXHffRNlWTmfUIUx_YtO9aVKL_hmfn5xVXbYS_5cSzuAm8cdr7zVBwpkXkwSqsSv4AbRHTeE7x0pUUgx1rgOgfQVWAYPeHvmRQtUuvvXuGQKIso69YTMPGrd7M9qiGSvyLmZK1ChARrMi6FQu7m5h1qYJAsHX5EP89d9te5GOYYrtyChKqJnnTb_IM8WJqZhf46G9ks3M0N-XV-VfanE35lLftSN4xD-wEBSenOuEj97p1PJgaqj24bte4uGcB_uQefYSd7eTRbYE8sFVLBlzfgftJO9ufWvUC2MjrBGJmXlJlxy9oW9TYcgnz2G1vIL8mo94ImjGajT2JteN6x2gDhTFRLXbct-Ti7r44ybP53L2g3lfzbb6JwKxSGNAQmvekH_5cIIwsIOYogT8MXkDdsyAjH5CPGlBcE1okKqG13SC9vToI470CSgwNGw-S4TxaVFHAlHJYi-I8A7Tun6JltDn4jrpQ4F6dk0yGNRyYFaq1olD8tB1W63B9-yyUGvAAm8_F4_YmfDtexhkyPfm3l5Ndg2r4-dmEz4CqXgsULdYtttulzEp-A4x0EviJtMeNvMdW-zZkr5V5OU-44W-EQcc5HdNyyuojH1Knaf-5y6TV1p4h_usu-yLRIpJx69lckGt04yhe7ukWBYoUDeCrxKuhheoxqAmrSzWDBfPVHUVyYVaqXQfd_PZ7h0AYASv5bZwvPNxJTayI-aAoMsSzoNj0bXjpdtkOJdl0N_LL-ajjkM_-aaDnYi6daiCT05iPH-bagO_TCkdaCZT9B-LoIclGUypapShFyhZP1DchCx4YYnscZAofMGtj6fLyZdCGTFkrM1PHkoDN-DNqD-pD9m8eV4kJKyOIYQjFh8ETLqvcPsG70upI1H6IjQHPVkTZSM7D5Zniu0XKDbyVrgWqWSXZ3_QQGKJq-dK71QoDBg1DnQHcICBVFiBVLOCOVUz8vxvNAuu_BkrTlbRPAO-6D41Tlo3_NK7_9d2-XsyLuduD_JSnMF-gBCReOROXmivv7CZnVQKXmCYqHNcs0BxBAuNCRFcP9m2lKDHgLy0zV_5Xs3trBjYu-Ie_QvNdVnymGslbZK4rf498Ekm1mz4K5jRn392FmfCE9HvUX7RlCI1Bv_7oF8TTxnOvZoiJdannDXnJfE=w1868-h938")
                await bttn.respond(embed=embed)
            except Exception as e:
                print(f"bttn ERROR [ABOUT CASHBACK] - {e}")
        case "Add vtuber":
            try:
                await add_vtuber(bttn)
            except Exception as e:
                print(f"bttn ERROR [ADD VTUBER] - {e}")
        case "Send Order":
            try:
                await send_order(bttn)
            except Exception as e:
                print(f"bttn ERROR [SEND ORDER] - {e}")
        case "Give an answer":
            try:
                await giveAnswer(bttn)
            except Exception as e:
                print(f"bttn ERROR [GIVE AN ANSWER] - {e}")
        case "Create promo":
            try:
                await create_promo(bttn)
            except Exception as e:
                print(f"bttn ERROR [CREATE PROMO] - {e}")
        case "Edit promo":
            try:
                await edit_promo(bttn)
            except Exception as e:
                print(f"bttn ERROR [EDIT PROMO] - {e}")
        case "Delete promo":
            try:
                await delete_promo(bttn)
            except Exception as e:
                print(f"bttn ERROR [DELETE PROMO] - {e}")
        case "Show all promo codes":
            try:
                await all_codes(bttn)
            except Exception as e:
                print(f"bttn ERROR [ALL CODES] - {e}")
        case "Send News":
            try:
                await news(bttn)
            except Exception as e:
                print(f"bttn ERROR [NEWS] - {e}")

        case "Enter edits":
            try:
                await bttn.respond()
            except Exception:
                pass
            await bttn.channel.send(embed=discord.Embed(title="Comment", description="Enter your comment", colour=discord.Color.blue()))
            await perms(bot.get_guild(guildID).get_member(bttn.author.id),bttn.channel , True)
            try:
                comment1 = await bot.wait_for("message", check=lambda i:i.channel.id == bttn.channel.id and i.author.id == bttn.author.id)
            except Exception:
                comment1 = ""
            await perms(bot.get_guild(guildID).get_member(bttn.author.id),bttn.channel , False)
            await bttn.channel.purge()
            comment = f'\nComment - {comment1.content}' if comment1.content != '' else ''
            msg1 = await bot.get_channel(admin_chn_id).send(bttn.author.mention, embed=discord.Embed(title="", description=f"The order has been sent for revision{comment}\n[ {bttn.channel.mention} ]", colour=discord.Color.red()),
                components=[
                    Button(style=ButtonStyle.green,label="Ok")
                ]
            )
            await bttn.channel.send(embed=discord.Embed(title="The order has been sent for revision", description="Your order has been sent for revision\nExpect Execution", colour=discord.Color.blue()), components=[])
        case "Approve the order":
            try:
                await bttn.respond()
            except Exception:
                pass
            msg1 = await bot.get_channel(admin_chn_id).send(bttn.author.mention, embed=discord.Embed(title="", description=f"The order has been approved\n[ {bttn.channel.mention} ]", colour=discord.Color.green()),components=[
                    Button(style=ButtonStyle.green,label="Ok")
                ])
            await bttn.message.edit(components=[])
            db.getsql(f"DELETE FROM Orders WHERE name = '{str(bttn.author)}' AND receipt_id = {bttn.channel.id}")
            db.getsql(f"UPDATE ConfirmedOrders SET isActive = 0 WHERE user_name = '{str(bttn.author)}' AND receipt_id = {bttn.channel.id}")
            if db.getsql(f"SELECT IsResponsed FROM Clients WHERE user_id = {bttn.author.id}")[0][0] == 0:
                await responseClient(bttn.channel)
            try:
                await msg1.delete()
            except Exception:
                pass
            return

        case "Ok":
            await bttn.message.delete()
        case "Show all confirmed orders":
            try:
                await all_orders(bttn)
            except Exception:
                pass
        case "Edit cashback":
            try:
                await edit_cashback(bttn)
            except Exception as e:
                print(f"bttn ERROR [EDIT CASHBACK] - {e}")
        case emj if emj in db.roles.keys():
            print("is emoji")
            try:
                try:
                    await bttn.respond()
                except Exception:
                    pass
                await bttn.author.add_roles(get(bot.get_guild(guildID).roles, id=db.roles[emj]))
            except Exception:
                pass

#----------------------------------BOT-COMMANDS----------------------------------------------#

@bot.command()
async def info(ctx):
    await ctx.author.send("Cashback is credited after each order in RC currency")

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, limit = 10):
    await ctx.channel.purge(limit = limit)

@bot.command()
@commands.has_permissions(administrator=True)
async def send_db(ctx):
    await ctx.send(file=discord.File("BaseData.db"))

#---------------------------------------------------------#

@bot.command()
@commands.has_permissions(administrator=True)
async def sql(ctx, *args : str):
    res = ""
    for i in db.getsql(' '.join(args)):
        res += f"{i}\n"
    await ctx.send(embed=discord.Embed(title="SQLite DATABASE return",description=res, colour=discord.Color.darker_grey()))

@bot.command()
@commands.has_permissions(administrator=True)
async def update_prices(ctx):

    answer1 = UpdatePrices()
    
    msg = await bot.get_channel(orders_chn_id).fetch_message(id=order_msg_id)
    await msg.edit(embed=discord.Embed(title="Menu",description=answer1, colour=discord.Color.blue())
    )


#---------------------------------------------------------#

@tasks.loop(seconds=30)
async def checkLiveStreamsTwitch():
    for id,streamer, place, status in db.getsql("SELECT id,streamer, place, status FROM LiveStreams WHERE place = 'TWITCH'"):
        info = CheckLiveStreamTwitch(streamer)
        match (info, status):
            case ("ERROR", _) | ("OFFLINE", "OFFLINE") | (None, "OFFLINE"):
                pass
            case ("OFFLINE", "LIVE"):
                db.getsql(f"""UPDATE LiveStreams SET status = 'OFFLINE' WHERE streamer = '{streamer}' AND place = '{place}'""")
            case (_, "OFFLINE"):
                try:
                    db.getsql(f"""UPDATE LiveStreams SET status = 'LIVE' WHERE streamer = '{streamer}' AND place = '{place}'""")
                    urlLive = f"https://www.twitch.tv/{info.streamer.lower()}"
                    embed = discord.Embed(title=info.title, colour=discord.Color.from_rgb(0, 250, 128), description=f"**{info.streamer}** started LIVE on **{place.lower().capitalize()}**\n\n[LIVE]({urlLive})")
                    try:
                        thumbnail_url = info.thumbnail_url.replace("-{width}x{height}", "")
                        embed.set_image(url=thumbnail_url)
                    except Exception:
                        pass

                    msg = await bot.get_channel(LIVE_NOW_CHN_ID).send(embed=embed)
                    await msg.publish()
                except Exception as E:
                    print("checkLiveStreamsTwitch - " + str(E))

@tasks.loop(minutes=15)
async def checkLiveStreamsYouTube():
    for id,streamer, place, status in db.getsql("SELECT id,streamer, place, status FROM LiveStreams"):
        info = CheckLiveStreamYoutube(id)
        match (info, status):
            case ("ERROR", _) | ("OFFLINE", "OFFLINE") | (None, "OFFLINE"):
                pass
            case ("OFFLINE", "LIVE"):
                db.getsql(f"""UPDATE LiveStreams SET status = 'OFFLINE' WHERE id = '{id}' AND place = '{place}'""")
            case (_, "OFFLINE"):
                try:
                    db.getsql(f"""UPDATE LiveStreams SET status = 'LIVE' WHERE id = '{id}' AND place = '{place}'""")
                    urlLive = f"https://www.youtube.com/channel/{id}/live"
                    embed = discord.Embed(title=info.title, colour=discord.Color.from_rgb(0, 250, 128), description=f"**{info.streamer}** started LIVE on **{place.lower().capitalize()}**\n\n[LIVE]({urlLive})")
                    try:
                        thumbnail_url = info.thumbnail_url
                        embed.set_image(url=thumbnail_url)
                    except Exception:
                        pass
                    msg = await bot.get_channel(LIVE_NOW_CHN_ID).send(embed=embed)
                    await msg.publish()
                except Exception as E:
                    print("checkLiveStreamsYouTube - " + str(E))
            
#-----------------------------------------RUN-BOT----------------------------------------#

bot.run(config.TOKEN)