from email.mime import base
import grequests, discord, datetime
from bs4 import BeautifulSoup as BS
import discord, asyncio, validators, youtube_api, config
from datetime import datetime, timedelta
from discord.ext.commands import Bot
from discord.utils import get
from discord import ButtonStyle, SelectOption, TextChannel
from discord.ui import Button, View, Select
import basedata

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
        return answer
    except Exception as E:
        print(f"Error - {E}")
        return

def GetPrices() -> dict:
    a = parseSite()
    prices = {}
    for title in a.keys():
        for i in a[title].keys():
            prices[i] = int(a[title][i]['Price'])
    return prices

def UpdatePrices():
    emojis = {"Mixing":"🎹","Instrumentals":"🎼","Tuning/Timing":"🎶","Producing":"🎤"}

    answer1 = ""
    a = parseSite()
    for title in a.keys():
        answer1+=f"**{emojis[title]} {title}**\n"
        for i in a[title].keys():
            answer1 += f"**•** *{i}* : {a[title][i]['disc']} - **{a[title][i]['Price']} $** {'minimum price' if title == 'Instrumentals' else 'per track' if i in ['Tuning', 'Timing'] else ''}\n"
        answer1 += "\n"
    return answer1

class ShopProcess():

    colorCategory : discord.Color

    def __init__(self, member : discord.Member, channel : discord.TextChannel, bot : Bot):
        self.member = member
        self.channel = channel
        self.bot = bot
        self.ListPrices = GetPrices()

    def GetPrice(self, category : str, categoryType : str, tracks : int | None, additional_option : list | None, active_price : int | None, promocode : tuple | None) -> int | float:
        perc = (1-(promocode[1]*0.01)) if promocode is not None else 1
        additional_option_price = 0
        if additional_option is not None and additional_option != []:
            for i in additional_option:
                additional_option_price += self.ListPrices[i] * (tracks if tracks is not None else 1) if i in ["Tuning", "Timing"] else self.ListPrices[i]
        if perc <= 0:
            perc = 1
        _tracks = tracks if tracks is not None else 1
        if category == "Mixing":
            return round(((self.ListPrices[categoryType]) + additional_option_price) * perc, 2)
        if active_price is not None:
            return round(active_price * perc,2)
        price = self.ListPrices[categoryType] if category != "Instrumentals" else self.price
        return round(((price * _tracks) + additional_option_price) * perc, 2)

    def promoUpdater(self, db : basedata.BaseData):
        for percent, StartPercent, Name, service in db.sqlite("SELECT percent, FirstPercent, Name, TypeService FROM Promocodes"):
            numsUsed = len(db.sqlite(f"SELECT user FROM UserPromo WHERE promocode = '{Name}' AND Category = '{service}'"))
            if percent - StartPercent < 25:
                match (numsUsed, percent - StartPercent):
                    case (5 | 6 | 7 | 8 | 9, 0) | (10 | 11 | 12 | 13 | 14, 5) | (15, 10):
                        db.sqlite(f"UPDATE Promocodes SET percent = {percent+5} WHERE Name = '{Name}' AND TypeService = '{service}'")

    def getDeadline(self, typecategory : str, db : basedata.BaseData, deadline : int | None, Additional_options : list | None) -> int:
        dictP = {
            "Solo" : 3,
            "Duo/Trio" : 4,
            "Chorus" : 5,
            "Loop Streaming BGM" : 10,
            "Custom Intro/Debut Trailer" : 10,
            "Tuning" : 4,
            "Timing" : 4,
            "Artificial harms" : 4,
            "Harms Guide" : 4,
        }
        if deadline is None:
            addopt = 4 if Additional_options is not None and len(Additional_options) >= 1 else 0
            return (dictP.get(typecategory, 0)) + addopt + (len(db.sqlite("SELECT * FROM Orders")) if len(db.sqlite("SELECT * FROM Orders")) > 1 else 0)
        return deadline + (len(db.sqlite("SELECT * FROM Orders")) if len(db.sqlite("SELECT * FROM Orders")) > 1 else 0)

    async def perms(self,member,channel, messageSender = False):
        perms = channel.overwrites_for(member)
        perms.send_messages = messageSender
        await channel.set_permissions(member, overwrite=perms)

    
    async def selectCategory(self) -> tuple | None:
        view=View()
        view.add_item(Button(label="Mixing", custom_id="Mixing", row=1))
        view.add_item(Button(label="Instrumentals", custom_id="Instrumentals", row=1))
        view.add_item(Button(label="Tuning/Timing", custom_id="Tuning/Timing", row=2))
        view.add_item(Button(label="Producing", custom_id="Producing", row=2))
        view.add_item(Button(label="BGM", custom_id="BGM", row=2))
        view.add_item(Button(style=ButtonStyle.danger, label="Cancel", custom_id="cancel",row=3))

        msg = await self.channel.send(self.member.mention,
            embed=discord.Embed(title="Select a service category",description=f"Selecet a service category", colour=discord.Color.blue()),
            view=view
        )

        response = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
        category = response.data.get("custom_id", None)
        await response.response.defer()

        if category is not None:
            match category:
                case "Mixing":
                    self.colorCategory = discord.Color.blue()
                case "Instrumentals":
                    self.colorCategory = discord.Color.dark_purple()
                case "Tuning/Timing":
                    self.colorCategory = discord.Color.dark_teal()
                case "Producing":
                    self.colorCategory = discord.Color.greyple()
                case "BGM":
                    self.colorCategory = discord.Color.blurple()

        return (category, msg) if category != "cancel" else (None, msg)

    async def selectTypeCategory(self,category : str, message : discord.Message) -> str | None:
        view=View()
        view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
        for type in config.categorys[category]:
            view.add_item(Button(label=type,custom_id=type, row=1))
        await message.edit(embed=discord.Embed(title="Type", description="Select type", colour=self.colorCategory),view=view)
        
        response = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
        categoryType = response.data.get("custom_id", None)
        await response.response.defer()
        return categoryType if categoryType != "back" else None

    async def enterDetails(self, message : discord.Message) -> dict | None:
        await message.edit(embed=discord.Embed(title="Details", description="Enter details", colour=self.colorCategory), view=View())
        await self.perms(self.member, self.channel, True)
        try:
            details = await self.bot.wait_for("message", check=lambda msg:msg.author.id == self.member.id and msg.channel.id == self.channel.id, timeout=3600)
        except asyncio.TimeoutError:
            await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
            await asyncio.sleep(10)
            await self.channel.delete()
            return None
        await details.delete()
        return {"Details" : details.content}

    async def enterLinks(self,category : str, categoryType : str, message : discord.Message) -> dict | None:
        result = {}
        if category == "Mixing":
            await message.edit(embed=discord.Embed(title="Link to the tracks", description="Send a link to the tracks", colour=self.colorCategory), view=View())
            await self.perms(self.member, self.channel, True)
            try:
                lnk = await self.bot.wait_for("message", check=lambda msg:msg.author.id == self.member.id and msg.channel.id == self.channel.id and validators.url(msg.content), timeout=600)
            except asyncio.TimeoutError:
                await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                await asyncio.sleep(10)
                await self.channel.delete()
                return None
            await self.perms(self.member, self.channel, False)
            result["Link"] = lnk.content
            await lnk.delete()
                        
        await message.edit(embed=discord.Embed(title="Link to the original video or reference", description="Send a link to the original video or reference", colour=self.colorCategory), view=View())
        await self.perms(self.member, self.channel, True)
        try:
            lnk = await self.bot.wait_for("message", check=lambda msg:msg.author.id == self.member.id and msg.channel.id == self.channel.id and validators.url(msg.content), timeout=600)
        except asyncio.TimeoutError:
            await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
            await asyncio.sleep(10)
            await self.channel.delete()
            return None
        await self.perms(self.member, self.channel, False)
        result["Original link"] = lnk.content
        await lnk.delete()

        if category != "Instrumentals" and categoryType != "Harms Guide" and categoryType != "Artificial harms" and categoryType != "Producing":
            await message.edit(embed=discord.Embed(title="Number of tracks in the project", description="Enter the number of tracks in the project", colour=self.colorCategory), view=View())
            await self.perms(self.member, self.channel, True)
            try:
                numb = await self.bot.wait_for("message", check=lambda msg:msg.author.id == self.member.id and msg.channel.id == self.channel.id and msg.content.isdigit() and int(msg.content) <= 1000, timeout=600)
            except asyncio.TimeoutError:
                await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                await asyncio.sleep(10)
                await self.channel.delete()
                return None
            await self.perms(self.member, self.channel, False)
            result['Tracks'] = int(numb.content)
            await numb.delete()

        view=View()
        view.add_item(Button(style=ButtonStyle.green,label="Continue", custom_id="Continue"))
        view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))

        Links = ""
        for key, value in result.items():
            Links+=f"**{key}** : {value}\n"

        await message.edit(embed=discord.Embed(description=Links, colour=self.colorCategory),
            view=view
        )

        try:
            isContinue = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id, timeout=600)
        except asyncio.TimeoutError:
            await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
            await asyncio.sleep(10)
            await self.channel.delete()
            return None

        await isContinue.response.defer()
        if isContinue.data.get("custom_id") == "back":
            return None

        return result

    async def additionalService(self,category : str, categoryType : str, message : discord.Message) -> list | None:
            Additional_options = []
            if category == "Producing":
                view = View()
                view.add_item(Button(style=ButtonStyle.green, label="Yes", custom_id="Yes", emoji="✅"))
                view.add_item(Button(label="Continue", custom_id="Continue"))
                view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
                await message.edit(
                    embed=discord.Embed(title="Great !", description="Do you want to choose additional services?", colour=self.colorCategory),
                    view=view
                )
                while True:
                    
                    try:
                        resp3 = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id, timeout=600)
                    except asyncio.TimeoutError:
                        await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                        await asyncio.sleep(10)
                        await self.channel.delete()
                        return None
                    try:
                        await resp3.response.send_message()
                    except Exception:
                        pass
                    match resp3.data.get("custom_id"):
                        case "back":
                            return None
                        case "Reset":
                            Additional_options = []
                            view=View()
                            view.add_item(Button(style=ButtonStyle.green, label="Choose more", custom_id="Choose more"))
                            view.add_item(Button(label="Continue", custom_id="Continue"))
                            await message.edit(
                            embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(Additional_options)), colour=self.colorCategory),
                                view=view
                            )
                            continue
                        case "Continue" | "No":
                            await message.edit(embed=discord.Embed(title="Great !", colour=discord.Color.green()), view=View())
                            break

                        case "Choose more" | "Yes":
                            view=View()
                            view.add_item(Button(label="Mixing", custom_id="Mixing"))
                            view.add_item(Button(label="Instrumentals", custom_id="Instrumentals"))
                            view.add_item(Button(label="Tuning/Timing", custom_id="Tuning/Timing"))
                            view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
                            await message.edit(
                                embed=discord.Embed(title="Additional services", colour=self.colorCategory),
                                view=view
                            )
                            try:
                                resp4 = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id, timeout=600)
                            except asyncio.TimeoutError:
                                await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                await asyncio.sleep(10)
                                await self.channel.delete()
                                return None
                            try:
                                await resp4.response.send_message()
                            except Exception:
                                pass
                            if resp4.data.get("custom_id") == "back":
                                view=View()
                                view.add_item(Button(style=ButtonStyle.green, label="Choose more", custom_id="Choose more"))
                                view.add_item(Button(label="Continue", custom_id="Continue"))
                                view.add_item(Button(label="Reset", custom_id="Reset"))
                                await message.edit(
                                    embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(Additional_options)), colour=self.colorCategory),
                                    view=view
                                )
                                continue
                            try:
                                view=View()
                                for bttn in config.categorys[resp4.data.get("custom_id")]:
                                    if bttn not in Additional_options:
                                        view.add_item(Button(label=bttn, custom_id=bttn))
                                view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))

                                await message.edit(
                                    embed=discord.Embed(title="Additional services", colour=self.colorCategory),
                                    view=view
                                )
                            except Exception as E:
                                print(str(E))
                                view=View()
                                view.add_item(Button(style=ButtonStyle.green, label="Choose more", custom_id="Choose more"))
                                view.add_item(Button(label="Continue", custom_id="Continue"))
                                view.add_item(Button(label="Reset", custom_id="Reset"))
                                await message.edit(
                                    embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(Additional_options)), colour=self.colorCategory),
                                    view=view
                                )
                                continue
                            typeResp = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
                            try:
                                await typeResp.response.send_message()
                            except Exception:
                                pass

                            
                            if typeResp.data.get("custom_id") != "back": Additional_options.append(typeResp.data.get("custom_id"))
                                        
                            view=View()
                            view.add_item(Button(style=ButtonStyle.green, label="Choose more", custom_id="Choose more"))
                            view.add_item(Button(label="Continue", custom_id="Continue"))
                            view.add_item(Button(label="Reset", custom_id="Reset"))
                            view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))

                            await message.edit(
                                embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(Additional_options)), colour=self.colorCategory),
                                view=view
                            )
                            continue
                
            elif category != "Instrumentals" and categoryType != "Harms Guide" and categoryType != "Artificial harms":
                view = View()
                view.add_item(Button(style=ButtonStyle.green, label="Yes", custom_id="Yes", emoji="✅"))
                view.add_item(Button(label="Continue", custom_id="Continue"))
                view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
                await message.edit(
                    embed=discord.Embed(title="Great !", description="Do you want to choose additional services?", colour=self.colorCategory),
                    view=view
                )
                while True:
                    try:
                        resp3 = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id, timeout=600)
                    except asyncio.TimeoutError:
                        await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                        await asyncio.sleep(10)
                        await self.channel.delete()
                        return None
                    try:
                        await resp3.response.send_message()
                    except Exception:
                        pass
                    match resp3.data.get("custom_id"):
                        case "back":
                            return None
                        case "Reset":
                            Additional_options = []
                            view=View()
                            view.add_item(Button(style=ButtonStyle.green, label="Choose more", custom_id="Choose more"))
                            view.add_item(Button(label="Continue", custom_id="Continue"))
                            await message.edit(
                                embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(Additional_options)), colour=self.colorCategory),
                                view=view
                            )
                            continue
                        case "Continue" | "No":
                            await message.edit(embed=discord.Embed(title="Great !", colour=discord.Color.green()), view=View())
                            break

                        case "Choose more" | "Yes":
                            view=View()
                            for bttn in config.categorys["Tuning/Timing"]:
                                if bttn not in Additional_options and bttn != categoryType:
                                    view.add_item(Button(label=str(bttn), custom_id=str(bttn)))
                            view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
                            await message.edit(
                                    embed=discord.Embed(title="Additional services\nTuning/Timing", colour=self.colorCategory),
                                    view=view
                                )
                            try:
                                resp4 = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
                            except asyncio.TimeoutError:
                                await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                                await asyncio.sleep(10)
                                await self.channel.delete()
                                return None
                           
                            await resp4.response.defer()
                            
                            if resp4.data.get("custom_id") != "back": Additional_options.append(resp4.data.get("custom_id"))
                            view=View()
                            view.add_item(Button(style=ButtonStyle.green, label="Choose more", custom_id="Choose more"))
                            view.add_item(Button(label="Continue", custom_id="Continue"))
                            view.add_item(Button(label="Reset", custom_id="Reset"))
                            await message.edit(
                                    embed=discord.Embed(title="Great !", description="Do you want to choose additional services?\n\n*You choose*:\n{}".format('\n'.join(Additional_options)), colour=self.colorCategory),
                                    view=view
                                )
                            continue
            return Additional_options

    async def enterPromocode(self,category : str,db : basedata.BaseData, message : discord.Message) -> tuple:
        percent = 100
        promocodeName : str = None
        view=View()
        view.add_item(Button(style=ButtonStyle.green, label="Use promo code", custom_id="Use promo code"))
        view.add_item(Button(label="No, Thanks", custom_id="No, Thanks"))
        view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
        await message.edit(
            embed=discord.Embed(title="Great !", description="will you use a promo code?", colour=self.colorCategory),
            view=view
        )
        try:
            resp5 = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
        except asyncio.TimeoutError:
            await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
            await asyncio.sleep(10)
            await self.channel.delete()
            return (None,None)
        await resp5.response.defer()
        match resp5.data.get("custom_id"):
            case "back":
                return (None,None)
                        
            case "Use promo code":
                await message.edit(embed=discord.Embed(title="Promo Code",description='Enter your promo code\n*or enter "skip"', colour=self.colorCategory), view=View())
                while True:
                    await self.perms(self.member, self.channel, True)

                    try:
                        promocode = await self.bot.wait_for("message", check=lambda i:i.author.id == self.member.id and i.channel.id == self.channel.id)
                    except asyncio.TimeoutError:
                        await self.channel.send(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                        await asyncio.sleep(10)
                        await self.channel.delete()
                        return (None,None)
                    await self.perms(self.member, self.channel, False)
                    if promocode.content.lower() == "skip":
                        await promocode.delete()
                        break
                    elif db.sqlite(f"SELECT Owner FROM Promocodes WHERE Owner = '{str(promocode.author)}' AND Name = '{promocode.content}' AND TypeService IN ('{category}', 'all')") != []:
                        await message.edit(embed=discord.Embed(title="Something went wrong",description='You cannot use your own promo code\nTry another promo code\nor enter "skip"', colour=discord.Color.dark_red()))
                        await promocode.delete()
                        continue
                    elif db.sqlite(f"SELECT user FROM UserPromo WHERE user = '{str(promocode.author)}' AND promocode = '{promocode.content}' AND Category = '{category}'") != []:
                        await message.edit(embed=discord.Embed(title="Something went wrong",description='You have already used this promo code\nTry another promo code\nor enter "skip"', colour=discord.Color.dark_red()))
                        await promocode.delete()
                        continue
                    elif db.sqlite(f"SELECT percent FROM Promocodes WHERE Name = '{promocode.content}' AND TypeService IN ('{category}', 'all')") == []:
                        await message.edit(embed=discord.Embed(title="Something went wrong",description='Incorrect promo code\nTry another promo code\nor enter "skip"', colour=discord.Color.dark_red()))
                        await promocode.delete()
                        continue
                    percent = db.sqlite(f"SELECT percent FROM Promocodes WHERE Name = '{promocode.content}' AND TypeService IN ('{category}', 'all')")[0][0]
                    promocodeName = promocode.content
                    await promocode.delete()
                    await message.edit(embed=discord.Embed(title="Great",colour=self.colorCategory), view=View())
                    break

                        
            case "No, Thanks":
                await message.edit(embed=discord.Embed(title="Great !", colour=self.colorCategory), view=View())
        if percent == 100 and db.sqlite(f"SELECT Name FROM Promocodes WHERE Owner = '{str(resp5.user)}'") != []:
            percent = int(db.sqlite(f"SELECT percent FROM Promocodes WHERE Owner = '{str(resp5.user)}'")[0][0])
            return (None,percent)
        return (promocodeName,percent)

    async def enterPrice(self,receipt : dict) -> tuple | None:
        admin_channel = self.bot.get_channel(config.admin_chn_id)
        receiptText = ""
        for key, value in receipt.items():
            if key == "Additional Options":
                receiptText += f"**{key}** : " + ", ".join(value) + "\n"
            elif key == "Deadline":
                receiptText += f"**{key}** : {value} days\n"
            elif key == "Price":
                receiptText += f"**{key}** : {value} $\n"
            elif key == "Promocode":
                receiptText += f"**{key}** : {value[0]} ({value[1]}%)\n" if value[0] is not None else f"**{key}** : ({value[1]}%)\n"
            else:
                receiptText += f"**{key}** : {value}\n"
        priceMsg = await admin_channel.send(embed=discord.Embed(title="RECEIPT", description=receiptText, colour=self.colorCategory))
        
        deadlinemsg = await admin_channel.send(f"<@{config.rero_id}>",embed=discord.Embed(title="Deadline", description="Enter the deadline", colour=self.colorCategory))
        deadline = await self.bot.wait_for("message", check=lambda msg:msg.author.id == config.rero_id and msg.channel.id == admin_channel.id and msg.content.isdigit())
        Deadline = int(deadline.content)

        msgExpect = await self.channel.send(embed=discord.Embed(title="Expect the price", description="Expect a price from the Administrator", colour=self.colorCategory))
        msgPrice = await admin_channel.send(f"<@{config.rero_id}>",embed=discord.Embed(title="Price", description="Enter the price", colour=self.colorCategory))
        price = await self.bot.wait_for("message", check=lambda msg:msg.author.id == config.rero_id and msg.channel.id == admin_channel.id and msg.content.isdigit())
        Price = int(price.content)
        await price.delete()

        try:
            await deadlinemsg.delete()
            await msgPrice.delete()
            await deadline.delete()
            await priceMsg.delete()
            await msgExpect.delete()
        except Exception:
            pass
        return (Deadline, Price)

    async def receipt(self, receipt : dict, db : basedata.BaseData, message : discord.Message) -> bool | None:
        admin_channel = self.bot.get_channel(config.admin_chn_id)
        receiptText = ""
        
        SpeedUps : bool = False
        cashback : int | None = None

        for key, value in receipt.items():
            if key == "Additional Options":
                if value is not None: receiptText += f"**{key}** : " + ", ".join(value) + "\n"
            elif key == "Deadline":
                receiptText += f"**{key}** : {value} days\n"
            elif key == "Price":
                receiptText += f"**{key}** : {value} $\n"
            elif key == "Promocode":
                receiptText += f"**{key}** : {value[0]} ({value[1]}%)\n" if value[0] is not None else f"**{key}** : ({value[1]}%)\n"
            else:
                receiptText += f"**{key}** : {value}\n"
        
        embedReceipt = discord.Embed(title="YOUR RECEIPT", description=receiptText,colour=self.colorCategory)
        await message.edit(
            embed=embedReceipt, view=View()
        )
        paypalEmj = get(self.channel.guild.emojis, name="paypal")
        wiseEmj = get(self.channel.guild.emojis, name="wise")
        view=View()
        view.add_item(Button(style=ButtonStyle.blurple,label="Wise.com", custom_id="Wise.com", emoji=wiseEmj))
        view.add_item(Button(style=ButtonStyle.blurple,label="PayPal", custom_id="PayPal", emoji=paypalEmj))
        view.add_item(Button(style=ButtonStyle.red,label="Reset", custom_id="Reset"))
        paymentMsg = await self.channel.send(
            embed=discord.Embed(title="Choose a payment method", colour=self.colorCategory),
            view=view
        )
        while True:
            if cashback is None and db.sqlite(f"SELECT Scores FROM Clients WHERE user_ID = {self.member.id}") != []:
                if db.sqlite(f"SELECT Scores FROM Clients WHERE user_ID = {self.member.id}")[0][0] != 0:
                    view.add_item(Button(
                        style=ButtonStyle.green,
                        label="Use cashback",
                        custom_id="Use cashback",
                        row=2)
                    )
                    await paymentMsg.edit(view=view)
                if not SpeedUps and receipt.get("Deadline", None) is not None:
                    view.add_item(Button(
                        style=ButtonStyle.green,
                        label="Speed up the deadline [+ 50% to the price]",
                        custom_id="Speed up the deadline",
                        row=2)
                    )
                    await paymentMsg.edit(view=view)
                receiptText = ""
                for key, value in receipt.items():
                    if key == "Additional Options":
                        receiptText += f"**{key}** : " + ", ".join(value) + "\n"
                    elif key == "Deadline":
                        receiptText += f"**{key}** : {value} days\n"
                    elif key == "Price":
                        receiptText += f"**{key}** : {value} $\n"
                    elif key == "Promocode":
                        receiptText += f"**{key}** : {value[0]} ({value[1]}%)\n" if value[0] is not None else f"**{key}** : ({value[1]}%)\n"
                    else:
                        receiptText += f"**{key}** : {value}\n"
                await paymentMsg.edit(
                    view=view
                )
            resp = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
            await resp.response.defer()
            match resp.data.get("custom_id"):
                case "Wise.com":
                    view=View()
                    view.add_item(Button(style=ButtonStyle.green, label="Payment made", custom_id="Payment made", emoji="✅"))
                    view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
                    await paymentMsg.edit(embed=discord.Embed(title="Receiver", description="""
    **Name**: Mala Svitlana
    **Postal Code**: 51925
    **Adress**: Ukraine, reg. Dnipropetrovska, city.Kamianske, street. Kostelna, build.8, fl.4
    **E-mail**: rcduocovers@gmail.com
    **IBAN**: UA533220010000026203311644991
    USD->UAH
                                    """,
                url="https://wise.com",
                colour=self.colorCategory), 
                view=view
            )
                case "PayPal":
                    view=View()
                    view.add_item(Button(style=ButtonStyle.green, label="Payment made", custom_id="Payment made", emoji="✅"))
                    view.add_item(Button(style=ButtonStyle.red, label="Back", custom_id="back", row=2))
                    await paymentMsg.edit(
                        embed=discord.Embed(title="PayPal",description="rcduocovers@gmail.com", colour=discord.Color.dark_blue()),
                        view=view
                    )

                case "Speed up the deadline":
                                SpeedUps = True
                                view=View()
                                view.add_item(Button(style=ButtonStyle.blurple,label="Wise.com", custom_id="Wise.com", emoji=wiseEmj))
                                view.add_item(Button(style=ButtonStyle.blurple,label="PayPal", custom_id="PayPal", emoji=paypalEmj))
                                view.add_item(Button(style=ButtonStyle.red,label="Reset", custom_id="Reset"))
                                receipt["Price"] *= 1.5
                                
                                priceMsg = await admin_channel.send(embed=discord.Embed(title="RECEIPT", description=receiptText, colour=self.colorCategory))
                                await paymentMsg.edit(embed=discord.Embed(title="Deadline", description="wait the deadline", colour=self.colorCategory), view=View())
                                deadlinemsg = await admin_channel.send(f"<@{config.rero_id}>",embed=discord.Embed(title="Deadline", description="Enter the deadline", colour=self.colorCategory))
                                deadline = await self.bot.wait_for("message", check=lambda i:i.author.id == self.member.id and i.channel.id == admin_channel.id and i.content.isdigit())
                                receipt["Deadline"] = int(deadline.content)
                                try:
                                    await deadlinemsg.delete()
                                    await priceMsg.delete()
                                    await deadline.delete()
                                except Exception:
                                    pass
                                receiptText = ""
                                for key, value in receipt.items():
                                    if key == "Additional Options":
                                        receiptText += f"**{key}** : " + ", ".join(value) + "\n"
                                    elif key == "Deadline":
                                        receiptText += f"**{key}** : {value} days\n"
                                    elif key == "Price":
                                        receiptText += f"**{key}** : {value} $\n"
                                    elif key == "Promocode":
                                        receiptText += f"**{key}** : {value[0]} ({value[1]}%)\n" if value[0] is not None else f"**{key}** : ({value[1]}%)\n"
                                    else:
                                        receiptText += f"**{key}** : {value}\n"
    
                                await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=self.colorCategory), view=view)
                                
                                embedCl = discord.Embed(title="YOUR RECEIPT", description=receiptText, colour=self.colorCategory)
                                await message.edit(
                                    embed=embedCl, view=View()
                                )
                                continue
                case "Use cashback":
                    cashback = db.sqlite(f"SELECT Scores FROM Clients WHERE user_ID = {resp.user.id}")[0][0]
                    #client1.isUsedCashback = True
                    receipt["Price"] *= 1-(cashback*0.01) if cashback <= 20 else 0.8
                    receipt["Price"] = round(receipt["Price"],2)
                    cashback -= cashback if cashback <= 20 else 20

                    receiptText = ""
                    for key, value in receipt.items():
                        if key == "Additional Options":
                            receiptText += f"**{key}** : " + ", ".join(value) + "\n"
                        elif key == "Deadline":
                            receiptText += f"**{key}** : {value} days\n"
                        elif key == "Price":
                            receiptText += f"**{key}** : {value} $\n"
                        elif key == "Promocode":
                            receiptText += f"**{key}** : {value[0]} ({value[1]}%)\n" if value[0] is not None else f"**{key}** : ({value[1]}%)\n"
                        else:
                            receiptText += f"**{key}** : {value}\n"

                    view=View()
                    view.add_item(Button(style=ButtonStyle.blurple,label="Wise.com", custom_id="Wise.com", emoji=wiseEmj))
                    view.add_item(Button(style=ButtonStyle.blurple,label="PayPal", custom_id="PayPal", emoji=paypalEmj))
                    view.add_item(Button(style=ButtonStyle.red,label="Reset", custom_id="Reset"))
                    await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=self.colorCategory), view=view)
                    
                    embedCl = discord.Embed(title="YOUR RECEIPT", description=receiptText, colour=self.colorCategory)
                    await message.edit(
                        embed=embedCl, view=View()
                    )
                    continue
                case "Reset":
                    try:
                        await resp.channel.purge()
                        return None
                        #del client1
                    except Exception:
                        pass

            confirm = await self.bot.wait_for("interaction", check=lambda i:i.user.id == self.member.id and i.channel.id == self.channel.id)
                            #---------------------------------------CONFIRM-----------------------------------------#
            await confirm.response.defer()
            if confirm.data.get("custom_id") == "Payment made":
                isBack = False
                await paymentMsg.edit(embed=discord.Embed(title="Screenshot or payment confirmation link",description='Send a screenshot or payment confirmation link',colour=self.colorCategory).set_footer(text='or type "back" to return to the payment method menu'), view=View())
                while True:
                    await self.perms(self.member, self.channel, True)
                    response1 = await self.bot.wait_for("message", check=lambda i:i.author.id != self.bot.user.id and self.member.id == i.author.id and i.channel.id == self.channel.id and (i.content).isdigit() == False)
                    viewAdmin = View()
                    viewAdmin.add_item(Button(style=ButtonStyle.green,label="Confirm", custom_id="Confirm", emoji="✅"))
                    viewAdmin.add_item(Button(style=ButtonStyle.red,label="Invalid link", custom_id="Invalid link"))
                    viewAdmin.add_item(Button(label="Remove the order", custom_id="Remove the order", emoji="❌"))
                    await self.perms(self.member, self.channel, False)
                    embedCl = discord.Embed(title="YOUR RECEIPT", description=receiptText, colour=self.colorCategory)        
                    if response1.content.lower() == "back":
                        try:
                            await response1.delete()
                        except Exception:
                            pass
                        view=View()
                        view.add_item(Button(style=ButtonStyle.blurple,label="Wise.com", custom_id="Wise.com", emoji=wiseEmj))
                        view.add_item(Button(style=ButtonStyle.blurple,label="PayPal", custom_id="PayPal", emoji=paypalEmj))
                        view.add_item(Button(style=ButtonStyle.red,label="Reset", custom_id="Reset"))
                        await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=self.colorCategory), view=view)
                        isBack = True
                        break

                    try:
                        f = await response1.attachments[0].to_file()
                        msg = await admin_channel.send(file=f,content=f"<@{config.rero_id}>", embed=embedCl,
                            view=viewAdmin
                        )
                        confirUrl = str(response1.attachments[0].url)
                    except IndexError:
                        msg = await admin_channel.send(content=f"<@{config.rero_id}>\n{response1.content}",embed=embedCl, 
                                view=viewAdmin
                        )
                        confirUrl = response1.content
                    finally:
                        try:
                            await response1.delete()
                        except Exception:
                            pass
                        await paymentMsg.edit(embed=discord.Embed(title="Wait for confirmation",description="Expect confirmation from administrators within 24 hours", colour=self.colorCategory), view=View())
                    respC = await self.bot.wait_for("interaction", check=lambda i:i.message.id == msg.id, timeout=86400)
                    await respC.response.defer()
                    match respC.data.get("custom_id"):
                                        case "Confirm":
                                            
                                            await respC.message.delete()
                                            dateOrder = datetime.now().strptime(str(datetime.now().strftime("%B/%d/%Y")),"%B/%d/%Y") + timedelta(days=receipt.get("Deadline", 0))
                                            await self.channel.purge()
                                            await self.channel.send(
                                                confirm.user.mention,
                                                embed=discord.Embed(
                                                    title="Confirmed",
                                                    description="Your order has been confirmed",
                                                    colour=discord.Color.green(),
                                                    timestamp=dateOrder).set_footer(text="deadline"),
                                                view=View())                    
                                            
                                            scores2 = db.sqlite(f"SELECT Scores FROM Clients WHERE user_id = {confirm.user.id}")
                                            scores = scores2[0][0] if scores2 != [] else 0

                                            #if client1.isUsedCashback:
                                            #    db.sqlite(f"UPDATE Clients SET Scores = {cashback} WHERE user_id = {resp.user.id}")

                                            #elif not client1.isUsedCashback:
                                            #    try:
                                            #        await confirm.user.send(f"Thank you for the order.  You have been awarded - {round(priceOrder*0.02, 2)} RC\nNew Balance : {scores + round(priceOrder*0.02, 2)}")
                                            #    except Exception:
                                            #        pass
                                            
                                            try:
                                                role = get(resp.guild.roles, id=924322390438199306)
                                                role1 = get(resp.guild.roles,id=924322816503971850)
                                                members = await resp.guild.fetch_member(confirm.user.id)
                                                lenID = len(db.sqlite(f"SELECT Orders FROM Clients WHERE user_id = {confirm.user.id}"))
                                            except Exception:
                                                pass
                                            id = 0
                                            if lenID <= 0:
                                                db.sqlite(f"INSERT INTO Clients VALUES({confirm.user.id}, 1, {scores + round(receipt.get('Price')*0.02, 2) if not True else scores}, 0)")
                                            else:
                                                db.sqlite(f"UPDATE Clients SET Scores = {scores + round(receipt.get('Price')*0.02, 2)} WHERE user_id = {confirm.user.id}")
                                                id = db.sqlite(f"SELECT Orders FROM Clients WHERE user_id = {confirm.user.id}")[0][0]
                                            if id >= 3:
                                                try:
                                                    await members.add_roles(role1)
                                                except Exception:
                                                    pass
                                                db.sqlite(f"UPDATE Clients SET Orders={id+1} WHERE user_id = {confirm.user.id}")
                                            
                                            elif id < 4:
                                                db.sqlite(f"UPDATE Clients SET Orders={id+1} WHERE user_id = {confirm.user.id}")
                                                try:
                                                    await members.add_roles(role)
                                                except Exception:
                                                    pass

                                            db.sqlite(f"INSERT INTO ConfirmedOrders VALUES ('{confirUrl}', '{receipt.get('Service')}', '{str(confirm.user)}', 1,{confirm.user.id}, {self.channel.id})")                               
                                            if receipt.get('Promocode', [None])[0] is not None : db.sqlite(f"INSERT INTO UserPromo VALUES('{str(confirm.user)}', '{receipt.get('Promocode')[0]}','{receipt.get('Service')}')")
                                            db.sqlite(f"INSERT INTO Orders VALUES({confirm.user.id}, {0}, '{str(confirm.user)}', '{receipt.get('Service')}', {self.channel.id})")

                                            self.promoUpdater(db)
                                            return True
                                        case "Invalid link":
                                            await self.channel.purge()
                                            await msg.delete()
                                            del msg
                                            paymentMsg = await self.channel.send(confirm.user.mention, embed=discord.Embed(title="Invalid link", description="Enter the correct link", colour=discord.Color.red()), view=View())
                                            continue
                                        case "Remove the order":
                                            await self.channel.purge()
                                            await msg.delete()
                                            
                                            await self.channel.send(confirm.user.mention, embed=discord.Embed(description="The order has been removed", colour=discord.Color.red()), view=View())
                                            await asyncio.sleep(5)
                                            try:
                                                await self.channel.delete()
                                            except Exception:
                                                pass
                if isBack:
                    isBack = False
                    continue
            elif confirm.data.get("custom_id") == "back":
                view=View()
                view.add_item(Button(style=ButtonStyle.blurple,label="Wise.com", custom_id="Wise.com"))
                view.add_item(Button(style=ButtonStyle.blurple,label="PayPal", custom_id="PayPal"))
                view.add_item(Button(style=ButtonStyle.red,label="Reset", custom_id="Reset"))
                await paymentMsg.edit(embed=discord.Embed(title="Choose a payment method", colour=self.colorCategory), view=view)
                continue
            
            break

async def responseClient(response_chn_admin_id : int, response_chn_id : int, bot : Bot, channel : TextChannel, db : basedata.BaseData):
    bttnsNum = [str(i) for i in range(1, 6)]
    bttnsNum.append('skip')
    view=View()
    for i in range(1, 6):
        view.add_item(Button(label=str(i), custom_id=str(i),row=1))
    view.add_item(Button(style=ButtonStyle.blurple,label="skip", custom_id="skip",row=2))
    msg = await channel.send(embed=discord.Embed(title="Response", description="Rate the quality of service provision from 1 to 5", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=view)
    try:
        ServiceProvision = await bot.wait_for("interaction", check=lambda i:i.data.get("custom_id") in bttnsNum and i.channel == channel, timeout=600)
    except asyncio.TimeoutError:
        await msg.delete()
        await channel.delete()
        return
    try:
        await ServiceProvision.response.send_message()
    except Exception:
        pass
    chnl = bot.get_channel(response_chn_admin_id)
    member = ServiceProvision.guild.get_member(ServiceProvision.user.id)
    usabComment = ""
    ServiceProvisionComment = ""

    if ServiceProvision.data.get("custom_id") == "skip":
        await msg.edit(embed=discord.Embed(title='Great', colour=discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"),view=View())
        await asyncio.sleep(600)
        try:
            await channel.delete()
        except Exception:
            pass
        return

    if ServiceProvision.data.get("custom_id") in ['3', '2', '1']:
        await msg.edit(embed=discord.Embed(description="What exactly did you not like?", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=View())
        perms = channel.overwrites_for(member)
        perms.send_messages = True
        await channel.set_permissions(member, overwrite=perms)

        try:
            serviceComment = await bot.wait_for("message", check=lambda i:i.channel == channel and i.author.id == member.id, timeout=600)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        perms = channel.overwrites_for(member)
        perms.send_messages = False
        await channel.set_permissions(member, overwrite=perms)
        ServiceProvisionComment = serviceComment.content
        await serviceComment.delete()
    view=View()
    for i in range(1, 6):
        view.add_item(Button(label=str(i), custom_id=str(i)))
    await msg.edit(embed=discord.Embed(title="Response", description="Rate the usability of the bot from 1 to 5", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=view)
    try:
        usability = await bot.wait_for("interaction", check=lambda i:i.data.get("custom_id") in bttnsNum and i.channel == channel and i.user.id  == member.id, timeout=600)
    except asyncio.TimeoutError:
        await msg.delete()
        await channel.delete()
        return
    try:
        await ServiceProvision.response.send_message()
    except Exception:
        pass
    if usability.data.get("custom_id") in ['3', '2', '1']:
        await msg.edit(embed=discord.Embed(description="What exactly did you not like?", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 15 min"), view=View())
        perms = channel.overwrites_for(member)
        perms.send_messages = True
        await channel.set_permissions(member, overwrite=perms)
        try:
            usabilityComment = await bot.wait_for("message", check=lambda i:i.channel == channel and i.author.id == member.id, timeout=900)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        perms = channel.overwrites_for(member)
        perms.send_messages = False
        await channel.set_permissions(member, overwrite=perms)
        usabComment = usabilityComment.content
        await usabilityComment.delete()


    await msg.edit(embed=discord.Embed(title="Response", description="Leave your comment for future users", colour = discord.Color.blue(), ), view=View())
    perms = channel.overwrites_for(member)
    perms.send_messages = True
    await channel.set_permissions(member, overwrite=perms)
    try:
        comment = await bot.wait_for("message", check=lambda i:i.channel == channel and i.author.id == member.id, timeout=600)
    except asyncio.TimeoutError:
        await msg.delete()
        await channel.delete()
        return
    perms = channel.overwrites_for(member)
    perms.send_messages = False
    await channel.set_permissions(member, overwrite=perms)
    await msg.edit(embed=discord.Embed(title="Great", description="Thanks for the feedback\nHave a nice day)", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=View())
    await comment.delete()
    await chnl.send(embed=discord.Embed(title="Response", description=f"""
    **Client** : {ServiceProvision.user.mention}
    **Quality of service provision** : {int(ServiceProvision.data.get("custom_id")) * "⭐"} {ServiceProvisionComment} 
    **Usability of the bot** : {int(usability.data.get("custom_id")) * "⭐"} {usabComment} 
    **Comment** : {comment.content}
    """, colour = discord.Color.blue()).set_thumbnail(url=ServiceProvision.user.avatar.url))

    await bot.get_channel(response_chn_id).send(embed=discord.Embed(title="Response", description=f"""
    **Client** : {ServiceProvision.user.mention}
    **Quality of service provision** : {int(ServiceProvision.data.get("custom_id")) * "⭐"}
    **Usability of the bot** : {int(usability.data.get("custom_id")) * "⭐"}
    **Comment** : {comment.content}
    """, colour = discord.Color.blue()).set_thumbnail(url=ServiceProvision.user.avatar.url))
    db.sqlite(f"UPDATE Clients SET IsResponsed = 1 WHERE user_id = {ServiceProvision.user.id}")
    await asyncio.sleep(7)
    await msg.delete()
    await asyncio.sleep(600)
    try:
        await channel.delete()
    except Exception:
        pass

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

def CheckLiveStreamTwitch(nickname : str) -> Stream | str:
    url = "https://api.twitch.tv/helix/streams?user_login=" + nickname
    HEADERS = {
        'Client-ID': config.TWITCH_CLIENT_ID,
        'userization': 'Bearer ' + config.TWITCH_SECRET_KEY
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

    

class AdminFunctions:
    
    async def responseClient(interaction : discord.Interaction,channel : discord.TextChannel, bot : Bot, db : basedata.BaseData):
        view=View()
        for i in range(1, 6):
            view.add_item(Button(label=str(i), custom_id=str(i),row=1))
        view.add_item(Button(style=ButtonStyle.blurple,label="skip", custom_id="skip",row=2))
        msg = await channel.send(embed=discord.Embed(title="Response", description="Rate the quality of service provision from 1 to 5", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=view)
        try:
            ServiceProvision = await bot.wait_for("interaction", check=lambda i: i.channel == channel, timeout=600)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        try:
            await ServiceProvision.response.send_message()
        except Exception:
            pass
        chnl = bot.get_channel(config.response_chn_admin_id)
        usabComment = ""
        ServiceProvisionComment = ""

        if ServiceProvision.data.get("custom_id") == "skip":
            await msg.edit(embed=discord.Embed(title='Great', colour=discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"),view=View())
            await asyncio.sleep(600)
            try:
                await channel.delete()
            except Exception:
                pass
            return

        if ServiceProvision.data.get("custom_id") in ['3', '2', '1']:
            await msg.edit(embed=discord.Embed(description="What exactly did you not like?", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=View())
            await channel.set_permissions(ServiceProvision.user, send_messages = True)
            try:
                serviceComment = await bot.wait_for("message", check=lambda i:i.channel == channel and i.author != bot.user, timeout=600)
            except asyncio.TimeoutError:
                await msg.delete()
                await channel.delete()
                return
            #await perms(interaction.guild.get_member(ServiceProvision.user.id),channel , False)
            ServiceProvisionComment = serviceComment.content
            await serviceComment.delete()
        view=View()
        for i in range(1, 6):
            view.add_item(Button(label=str(i), custom_id=str(i)))
        await msg.edit(embed=discord.Embed(title="Response", description="Rate the usability of the bot from 1 to 5", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=view)
        try:
            usability = await bot.wait_for("interaction", check=lambda i:i.channel.id == channel.id and interaction.user.id == i.user.id, timeout=600)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        try:
            await ServiceProvision.response.send_message()
        except Exception:
            pass
        if usability.data.get("custom_id") in ['3', '2', '1']:
            await msg.edit(embed=discord.Embed(description="What exactly did you not like?", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 15 min"), view=View())
            await channel.set_permissions(ServiceProvision.user, send_messages = True)
            try:
                usabilityComment = await bot.wait_for("message", check=lambda i:i.channel == channel, timeout=900)
            except asyncio.TimeoutError:
                await msg.delete()
                await channel.delete()
                return
            usabComment = usabilityComment.content
            await usabilityComment.delete()


        await msg.edit(embed=discord.Embed(title="Response", description="Leave your comment for future users", colour = discord.Color.blue(), ), view=View())
        await channel.set_permissions(ServiceProvision.user, send_messages = True)
        try:
            comment = await bot.wait_for("message", check=lambda i:i.channel == channel, timeout=600)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.delete()
            return
        #await perms(interaction.guild.get_member(ServiceProvision.user.id),channel , False)
        await msg.edit(embed=discord.Embed(title="Great", description="Thanks for the feedback\nHave a nice day)", colour = discord.Color.blue()).set_footer(text="This channel will be deleted in 10 min"), view=View())
        await comment.delete()
        await chnl.send(embed=discord.Embed(title="Response", description=f"""
        **Client** : {ServiceProvision.user.mention}
        **Quality of service provision** : {ServiceProvision.data.get("custom_id")} {ServiceProvisionComment} 
        **Usability of the bot** : {usability.data.get("custom_id")} {usabComment} 
        **Comment** : {comment.content}
        """, colour = discord.Color.blue()).set_thumbnail(url=ServiceProvision.user.avatar.url))

        await bot.get_channel(config.response_chn_id).send(embed=discord.Embed(title="Response", description=f"""
        **Client** : {ServiceProvision.user.mention}
        **Quality of service provision** : {ServiceProvision.data.get("custom_id")}
        **Usability of the bot** : {usability.data.get("custom_id")}
        **Comment** : {comment.content}
        """, colour = discord.Color.blue()).set_thumbnail(url=ServiceProvision.user.avatar.url))
        db.sqlite(f"UPDATE Clients SET IsResponsed = 1 WHERE user_id = {ServiceProvision.user.id}")
        await asyncio.sleep(7)
        await msg.delete()
        await asyncio.sleep(600)
        try:
            await channel.delete()
        except Exception:
            pass

    async def edit_cashback(interaction : discord.Interaction, bot : Bot, db : basedata.BaseData):
        await interaction.response.defer()
        msg = await interaction.channel.send(embed=discord.Embed(title="Users cachback",description="Enter username", colour=discord.Color.teal()))
        resp = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and bool(len(i.mentions)) and interaction.user.id == i.author.id)
        user_id = resp.mentions[0].id
        try:
            await resp.delete()
        except Exception:
            pass
        if db.sqlite(f"SELECT Scores FROM Clients WHERE user_id = {user_id}") == []:
            await msg.edit(embed=discord.Embed(title="Users cachback",description=f"Sorry, but <@{user_id}> is not a customer (and has not made any order)", colour=discord.Color.teal()))
            await asyncio.sleep(7)
            try:
                await msg.delete()
            except Exception:
                pass
            return
        newCashback = 0
        activeCashback = db.sqlite(f"SELECT Scores FROM Clients WHERE user_id = {user_id}")[0][0]
            
        await msg.edit(embed=discord.Embed(title="Cashback", description=f"Active Cashback - {activeCashback} $\nEnter the cashback", colour=discord.Color.teal()), view=View())
        newCashbackMsg = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
        newCashback = newCashbackMsg.content
        try:
            await newCashbackMsg.delete()
        except Exception:
            pass
        view=View()
        view.add_item(Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id=f"change_cashback_{newCashback}_{user_id}"))
        view.add_item(Button(style=ButtonStyle.red, label="Cancel", custom_id="ok"))
        await msg.edit(
                embed=discord.Embed(title="Is correct?",description=f"Client : <@{user_id}>\n cashback : {newCashback} $", colour=discord.Color.teal()),
                view=view
            )

    async def add_vtuber(interaction : discord.Interaction, bot : Bot, db : basedata.BaseData, yt : youtube_api.YouTubeDataAPI):
        await interaction.response.defer()

        promocode : str
        id_channel : str
        platform : str
        user_name : str

        while True:

            msg = await interaction.channel.send(embed=discord.Embed(title="Member",description="Enter the Member", colour=discord.Color.blurple()))
            GetUser = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id and len(i.mentions) > 0)
            member = GetUser.mentions[0]
            await GetUser.delete()

            view = View()
            view.add_item(Select(
                    placeholder="Select a service category",
                    options = [
                        SelectOption(label="Twitch", value="TWITCH"),
                        SelectOption(label="Youtube", value="YOUTUBE")
                    ]
                ))

            await msg.edit(
            embed=discord.Embed(title="Platform",description="Select a Platform", colour=discord.Color.greyple()),
            view=view, #colour=discord.Color.blurple()
        ) 
            resp = await bot.wait_for("interaction", check=lambda i: i.data.get('values')[0] in ("TWITCH","YOUTUBE") and i.channel == interaction.channel and interaction.user.id == i.user.id)
            platform = resp.data.get('values')[0]

            try:
                await resp.response.send_message()
            except Exception:
                pass
            if platform == "YOUTUBE": 
                await msg.edit(embed=discord.Embed(title="Channel",description="Enter the channel user", colour=discord.Color.blurple()), view=View())
                id1 = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
                user_name = id1.content
                id_channel = yt.get_channel_id_from_user(id1.content)
                id_channel = id_channel if id_channel is not None else user_name
                await id1.delete()
            elif platform == "TWITCH":
                await msg.edit(embed=discord.Embed(title="Streamer name", description="Enter the streamer name", colour=discord.Color.blurple()), view=View())
                user_name1 = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
                user_name = user_name1.content
                await user_name1.delete()

            await msg.edit(embed=discord.Embed(title="Promocode",description="Enter the promo code", colour=discord.Color.blurple()))
            promocode_msg = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
            promocode = promocode_msg.content
            await promocode_msg.delete()

            urlLive = f"https://www.twitch.tv/{user_name}" if platform == "TWITCH" else f"https://www.youtube.com/channel/{id_channel}"
            view=View()
            view.add_item(Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id="button_yes", row=1))
            view.add_item(Button(label="No", emoji="❌", custom_id="button_no", row=1))
            view.add_item(Button(style=ButtonStyle.red, label="Cancel", custom_id="Cancel", row=2))
            await msg.edit(
                embed=discord.Embed(title="Is correct?",description=f"Member : {member}\nPromocode : {promocode} (10%)\n[LINK TO {'CHANNEL' if platform == 'YOUTUBE' else 'STREAMER'}]({urlLive})", colour=discord.Color.greyple()),
                view=view
            )#------------------------WAIT-FOR-CLICK-BUTTON---------------------------#

            resp1 = await bot.wait_for("interaction")
            try:
                await resp1.response.send_message()
            except Exception:
                pass
            if resp1.data.get("custom_id") == "button_yes":
                try:
                    role = get(interaction.guild.roles, id=1019132409431719957)
                    await member.add_roles(role)  # type: ignore
                except Exception:
                    pass
                db.sqlite(f"INSERT INTO LiveStreams({'id' if platform == 'YOUTUBE' else 'streamer'}, place, status) VALUES ('{id_channel if platform == 'YOUTUBE' else user_name}', '{platform}', 'OFFLINE')")
                db.sqlite(f"INSERT INTO Promocodes VALUES ('all', 10, '{promocode}', '{member}', 10)")
                await msg.edit(embed=discord.Embed(title="Great", colour=discord.Color.greyple()), view=View())
                await asyncio.sleep(5)
                await msg.delete()
                break
            elif resp1.data.get("custom_id") == "button_no":
                try:
                    await msg.delete()
                except Exception:
                    pass
                continue
            await msg.delete()
            break

    async def give_an_answer(interaction : discord.Interaction,bot : Bot, db : basedata.BaseData):
        messages = ""
        lastQuestion = ""
        for question, answer in db.sqlite(f"SELECT question, answer FROM Questions WHERE user_id = {interaction.user.id}"):
            messages += f"\n\n**Question** :\n{question}\n\n**Answer** :\n{answer}"
            lastQuestion = question
        msg = await interaction.user.send(embed=discord.Embed(title="Answer",description=f"Give an answer to **{interaction.user.name}**\n**Message history** : {messages}", colour=discord.Color.greyple()), view=View())
        user = await interaction.guild.fetch_member(db.sqlite(f"SELECT user_id FROM Questions WHERE name = {interaction.user.id}")[0][0])
        dm_channel = await user.create_dm()

        answer = await bot.wait_for("message", check=lambda i:i.channel.id == interaction.channel_id and i.author != bot.user)
        db.sqlite(f"UPDATE Questions SET answer = '{answer.content}' WHERE question = '{lastQuestion}' AND name = {interaction.user.id}")
        description = f"**To {interaction.user.name}** :"
        await answer.delete()
        for question, answer in db.sqlite(f"SELECT question, answer FROM Questions WHERE name = {interaction.user.id}"):
            description += f"\n\n**Question** :\n{question}\n\n**Answer** :\n{answer}"
        view=View()
        view.add_item(Button(style=ButtonStyle.green, label="Yes", custom_id="Yes", emoji="✅"))
        view.add_item(Button(label="No", custom_id="No", emoji="❌"))
        await dm_channel.send(embed=discord.Embed(title="Answer", description=description + '\n\nIs your question resolved?', colour=discord.Color.blurple()), 
            view=view
        )
        await msg.delete()
        try:
            isResolved = await bot.wait_for("interaction", check=lambda i:i.data.get("custom_id") in ["Yes", "No"] and i.user.id == interaction.user.id and i.user.id != bot.user.id, timeout=86400)
        except asyncio.TimeoutError:
            await dm_channel.send(view=View())
            db.sqlite(f"DELETE FROM Questions WHERE name = {interaction.user.id}")
            return
            
        await isResolved.response.defer()

    async def all_codes(interaction : discord.Interaction, bot : Bot, db : basedata.BaseData):
        view = View()
        view.add_item(Select(
                    placeholder="Select a service category",
                    options = [
                        SelectOption(label="Mixing", value="Mixing"),
                        SelectOption(label="Instrumentals", value="Instrumentals"),
                        SelectOption(label="Tuning/Timing", value="Tuning/Timing"),
                        SelectOption(label="Producing", value="Producing"),
                        SelectOption(label="All", value="all")
                    ]
                ))
        await interaction.response.send_message(
            embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
            view=view, 
        )
        resp = await bot.wait_for("interaction", check=lambda i: i.channel.id == interaction.channel_id and i.type == discord.InteractionType.component and i.data.get("component_type")==3)
        type_service = resp.data.get("values")[0]
        codes = ""
        for name, percent, owner in db.sqlite(f"SELECT Name, percent, Owner FROM Promocodes WHERE TypeService = '{type_service}'"): 
            nums = len(db.sqlite(f"SELECT promocode FROM UserPromo WHERE promocode = '{name}'"))
            codes += f"**Promocode** : {name} / *{percent}*%  [ **{nums}** ] {f'- {owner}' if owner != None else ''}\n"
        await resp.response.edit_message(embed=discord.Embed(title=type_service,description=codes, colour=discord.Color.greyple()), view=View().add_item(Button(label="Ok", custom_id="ok")))

    async def delete_promo(interaction : discord.Interaction, bot : Bot, db : basedata.BaseData):
        await interaction.response.defer()

        type_service : str

        view = View()
        view.add_item(Select(placeholder="Select a service category",options=[
            SelectOption(label="Mixing", value="deletepromo_Mixing"),
            SelectOption(label="Instrumentals", value="deletepromo_Instrumentals"),
            SelectOption(label="Tuning/Timing", value="deletepromo_Tuning/Timing"),
            SelectOption(label="Producing", value="deletepromo_Producing"),
            SelectOption(label="All", value="deletepromo_all")
        ]))

        msg = await interaction.channel.send(
        embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
        view=view, #colour=discord.Color.blurple()
        ) 
        resp = await bot.wait_for("interaction", check=lambda i: "deletepromo_" in i.data.get("values")[0] and i.channel == interaction.channel and interaction.user.id == i.user.id)
        type_service = resp.data.get("values")[0].split('_')[-1]

        await resp.response.defer()

        await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the promo code", colour=discord.Color.blurple()), view=View())
        name = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
        name1 = name.content
        await name.delete()

        view=View()
        view.add_item(Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id=f"delete_promo_{type_service}_{name1}"))
        view.add_item(Button(style=ButtonStyle.red, label="Cancel", custom_id="ok"))
        await msg.edit(
            embed=discord.Embed(title="Is correct?",description=f"Type service : {type_service}\nPromo Code : {name1}", colour=discord.Color.greyple()),
            view=view
        )
        
    async def edit_promocode(interaction : discord.Interaction, bot : Bot, db : basedata.BaseData):
        await interaction.response.defer()
        name : str
        percent : int
        type_service : str

        a = ("Mixing1", "Instrumentals1", "Tuning/Timing1", "Producing1")
        view = View()
        view.add_item(Select(placeholder="Select a service category",options=[
            SelectOption(label="Mixing", value="editpromocode_Mixing"),
            SelectOption(label="Instrumentals", value="editpromocode_Instrumentals"),
            SelectOption(label="Tuning/Timing", value="editpromocode_Tuning/Timing"),
            SelectOption(label="Producing", value="editpromocode_Producing")
        ]))
        while True:

            msg = await interaction.channel.send(
            embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.greyple()),
            view=view, #colour=discord.Color.blurple()
        ) 
            resp = await bot.wait_for("interaction", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.user.id)
            type_service = resp.data.get("values")[0].split('_')[-1]

            await resp.response.defer()

            percent = 0
            newOwner = ""
            while True:
                await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the promo code", colour=discord.Color.blurple()), view=View())
                name = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
                name1 = name.content
                await name.delete()

                await msg.edit(embed=discord.Embed(title="Percent",description="select percentage of promo code", colour=discord.Color.blurple()), view=View())
                try:
                    percentMsg = await bot.wait_for("message", check=lambda i: (i.content).isdigit() and i.channel == interaction.channel and interaction.user.id == i.author.id)
                    percent = int(percentMsg.content)
                    await percentMsg.delete()
                except TypeError:
                    await interaction.channel.send(embed=discord.Embed(description="you did not enter a number", colour=discord.Color.red()))
                    continue
                await msg.edit(embed=discord.Embed(title="Promo code", description="Enter the Owner of the promo code", colour=discord.Color.blurple()), view=View())
                owner = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel and interaction.user.id == i.author.id)
                newOwner = owner.mentions[0] if bool(len(owner.mentions)) else owner.content
                await owner.delete()
                break
            
            view=View()
            view.add_item(Button(style=ButtonStyle.green, label="Sure", emoji="✅", custom_id=f"edit_promocode_{type_service}_{name1}_{percent}_{newOwner.id}"))
            view.add_item(Button(style=ButtonStyle.red, label="Cancel", custom_id="ok"))
            await msg.edit(
                embed=discord.Embed(title="Is correct?",description=f"Type service : {type_service}\nPromo Code : {name1}\nPercent : {percent}%\nOwner : {newOwner}", colour=discord.Color.greyple()),
                view=view
            )
            break
    
    async def send_order(interaction : discord.Interaction, bot : Bot, db : basedata.BaseData):
        await interaction.response.defer()
        try:
            options = []
            for name, receipt_id, category1 in db.sqlite("SELECT name, receipt_id, category FROM Orders LIMIT 25"):
                options.append(SelectOption(label=name, value=receipt_id, description=f"Category : {category1}", emoji="👤"))

            view=View()
            view.add_item(Select(
                        placeholder="Select a client",
                        options = options
                    ))
            msg1 = await interaction.channel.send(
                embed=discord.Embed(title="Client",description="Select a client", colour=discord.Color.greyple()),
                view=view)

            resp = await bot.wait_for("interaction", check=lambda i: i.channel == interaction.channel and interaction.user != bot.user)
            idChn = resp.data.get("values")[0]
            await resp.response.defer()
            client = db.sqlite(f"SELECT name FROM Orders WHERE receipt_id = {idChn}")[0][0]
            idClient = db.sqlite(f"SELECT user_id FROM Orders WHERE name = '{client}' and receipt_id = {idChn} LIMIT 1")[0][0]
            await msg1.edit(embed=discord.Embed(title="Send Files", description=f"Send files to <#{idChn}>", colour=discord.Color.blue()), view=View())
            files1 = await bot.wait_for("message", check=lambda i:i.channel == interaction.channel)
            
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
            view=View()
            view.add_item(Button(style=ButtonStyle.green, label="Approve the order", custom_id=f"approve_order"))
            view.add_item(Button(label="Enter edits", custom_id="enter_edits"))
            try:
                await chn.send(f"<@{idClient}>",embed=discord.Embed(title="Your order is ready!", description=f"Files:\n{files1.content}", colour=discord.Color.blue()), files=listFiles, 
                view=view)
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
            print(str(E))
            m = await interaction.channel.send(embed=discord.Embed(title="No orders", colour=discord.Color.red()))
            await asyncio.sleep(5)
            await m.delete()
            return
