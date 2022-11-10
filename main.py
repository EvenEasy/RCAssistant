import discord, functions, config, youtube_api, asyncio, modals, random
from functions import AdminFunctions
from basedata import BaseData
from datetime import datetime
from discord.ext import commands, tasks
from discord.utils import get
from discord import ButtonStyle, app_commands
from discord.ui import Button, View
from functions import ShopProcess

bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())
db = BaseData("BaseData.db")
pingUser = 13404659964601958
yt = youtube_api.YouTubeDataAPI(config.GOOGLE_YOUTUBE_DATA_API_KEY)
tree = bot.tree

'''
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
'''

#----------------------------------------------#

guildID = 940590174117691462

CategoryOrdersID = 964881334512283668

welcome_chn_id = 924310034639372338
orders_chn_id = 964881858166939658
admin_chn_id = 964881972059066438
roles_chn_id = 964881949950885938

order_msg_id = 1029471950155821066

LIVE_NOW_CHN_ID = 964882860563632138

response_chn_admin_id = 964882836890988584
response_chn_id = 964882860563632138


@tree.command(name="sql", description="Contact with db", guild=discord.Object(guildID))
@app_commands.describe(
    sql = "Sqlite code"
)
async def _sqlite(interaction : discord.Interaction, sql : str):
    embed = discord.Embed(
        title="SQL DB RETURNED",
        description=db.sqlite(sql),
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(ephemeral=True, embed=embed)

@tree.command(name="send_db", description="Send DataBase file", guild=discord.Object(guildID))
async def _sqlite(interaction : discord.Interaction):
    await interaction.response.send_message(ephemeral=True, file=discord.File("BaseData.db"))

@tree.command(name="update_prices", description="Update prices", guild=discord.Object(guildID))
async def _sqlite(interaction : discord.Interaction):
    msg = await bot.get_channel(orders_chn_id).fetch_message(order_msg_id)
    await msg.edit(embed=discord.Embed(title="Menu",description=functions.UpdatePrices(), colour=discord.Color.blue()))
    embed = discord.Embed(
        title="Great",
        description="Prices have been updated successfully",
        color=discord.Color.green()
    )
    await interaction.response.send_message(ephemeral=True, embed=embed)


@bot.event
async def on_member_join(member: discord.Member):
    welcome_ch = bot.get_channel(welcome_chn_id)     # welcome channel                  # general chat
    embed = discord.Embed(title="WELCOME", description=f"""
        WELCOME TO **{bot.get_guild(guildID).name}** SERVER
        {member.mention}

        <#919009200682721300> - Information of the SERVER
        <#921533988374478858> - News of the SERVER
        <#924310974545149993> - Roles of the SERVER

    """, colour=discord.Color.magenta())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_image(url=random.choice(db.animeGifs))
    await welcome_ch.send(embed=embed)

@bot.event
async def on_member_remove(member):
    welcome_ch = bot.get_channel(welcome_chn_id)     # welcome channel
    embed = discord.Embed(description=f"""
{str(member)} LEFT US
we will miss you !
    """, colour=discord.Color.dark_red())
    embed.set_image(url=random.choice(db.animeGifsBye))
    await welcome_ch.send(embed=embed)
    

@bot.event
async def on_ready():
    print(f"[ {bot.user} ] BOT is connected")
    await tree.sync(guild=discord.Object(guildID))

    msg = await bot.get_channel(orders_chn_id).fetch_message(order_msg_id)
    await msg.edit(embed=discord.Embed(title="Menu",description=functions.UpdatePrices(), colour=discord.Color.blue()))

    adminCHn = bot.get_channel(admin_chn_id)
    viewAdmin = View()
    msg = await adminCHn.fetch_message(1029471947551146075)
    viewAdmin.add_item(Button(style=ButtonStyle.green,label="Send Order", custom_id="send_order", row=1))
    viewAdmin.add_item(Button(label="Show all confirmed orders", custom_id="show_all_confirmed_orders", row=1))

    viewAdmin.add_item(Button(style=ButtonStyle.blurple,label="Create promo", custom_id="create_promocode", row=2))
    viewAdmin.add_item(Button(style=ButtonStyle.blurple,label="Add vtuber", custom_id="add_vtuber", row=2))
    viewAdmin.add_item(Button(label="Edit promo", custom_id="edit_promocode", row=2))
    viewAdmin.add_item(Button(label="Delete promo", custom_id="delete_promocode", row=2))

    viewAdmin.add_item(Button(label="Show all promo codes", custom_id="all_codes", row=3))
    viewAdmin.add_item(Button(label="Edit cashback", custom_id="change_cashback", row=3))
    viewAdmin.add_item(Button(label="Send News", custom_id="create_news", row=3))

    await msg.edit(view=viewAdmin)

    # create-an-order channel
    orderChn = bot.get_channel(orders_chn_id)
    view = View()
    msg1 = await orderChn.fetch_message(order_msg_id)
    view.add_item(Button(style=ButtonStyle.green,label="Create an order", custom_id="create_an_order", emoji="🛒", row=1))
    view.add_item(Button(style=ButtonStyle.gray, label="Ask question", custom_id="support", emoji="❔",row=1))
    view.add_item(Button(style=ButtonStyle.blurple, label="My cashback", custom_id="my_cashback_balance",emoji="💰", row=1))
    view.add_item(Button(style=ButtonStyle.blurple, label="About cashback", custom_id="about_cashback", emoji="ℹ️", row=1))
    await msg1.edit(view=view)

    checkLiveStreamsTwitch.start()
    checkLiveStreamsYouTube.start()

@bot.listen()
async def on_interaction(interaction : discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data.get("component_type", None) == 2:
        match interaction.data.get("custom_id").split('_'):
            #---------------CREATE-AN-ORDER------------#
            case ["create", "an", "order"]:
                category = get(interaction.guild.categories, id=CategoryOrdersID)

                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                    interaction.guild.get_member(interaction.user.id): discord.PermissionOverwrite(read_messages=True, send_messages=False)
                }
                now = datetime.now()
                date1 = now.strftime("%d%m%Y")
                db.OrderId = db.sqlite("SELECT NumOrder FROM Info")[0][0] + 1
                db.sqlite(f"UPDATE Info SET NumOrder = {db.OrderId}")
                channel = await interaction.guild.create_text_channel(f"{str(interaction.user).split('#')[0]}_{db.OrderId}_{date1}", overwrites=overwrites, category=category)

                orderProcess = ShopProcess(interaction.user, channel, bot,)

                await interaction.response.send_message(ephemeral=True,embed=discord.Embed(title="Create an order", description=f"Your channel has been created {channel.mention}", colour=discord.Color.blue()))
                step = 0
                while True:
                    match step:
                        case 0:
                            category,msg = await orderProcess.selectCategory()
                            step=1
                            if category is None:
                                await channel.delete()
                                return
                        case 1:
                            typeCategory = await orderProcess.selectTypeCategory(category, msg)

                            receipt = {
                                "Client" : interaction.user.mention,
                                "Service" : category,
                                "Type" : typeCategory
                            }
                            
                            step = 2 
                            if typeCategory is None:
                                step = 0
                                await msg.delete()
                        case 2:
                            if category == "BGM":
                                details = await orderProcess.enterDetails(msg)
                                receipt=receipt | details
                                step = 4 if details is not None else 1
                                continue

                            links = await orderProcess.enterLinks(category,typeCategory,msg)
                            step = 3
                            if links is None:
                                step = 1
                                continue
                            receipt=receipt | links
                        case 3:
                            additionalOptions = await orderProcess.additionalService(category, typeCategory, msg)
                            if additionalOptions != []: receipt["Additional Options"] = additionalOptions
                            step = 4 if additionalOptions is not None else 2
                        case 4:
                            promocode,percent = await orderProcess.enterPromocode(category, db,msg)
                            if percent is not None and percent != 100: receipt["Promocode"] = (promocode,percent)
                            step = 5 if percent is not None else 3
                        case 5:
                            if category == "Instrumentals":
                                receipt["Deadline"], receipt["Price"] = await orderProcess.enterPrice(receipt)
                                
                            receipt["Deadline"] = orderProcess.getDeadline(
                                typeCategory,
                                db,
                                receipt.get("Deadline", None),
                                receipt.get("Additional Options",None)
                            )
                            receipt["Price"] = orderProcess.GetPrice(
                                category, 
                                typeCategory,
                                receipt.get("Tracks",None),
                                receipt.get("Additional Options",None),
                                receipt.get("Price",None),
                                receipt.get("Promocode", None)
                            )
                            receipt = await orderProcess.receipt(receipt, db, msg)
                            if receipt is None:
                                step = 0
                                continue
                            break

            case ["my","cashback", "balance"]:
                try:
                    if db.sqlite(f"SELECT Scores FROM Clients WHERE user_id = {interaction.user.id}") != []:
                        cachback = db.sqlite(f"SELECT Scores FROM Clients WHERE user_id = {interaction.user.id}")[0][0]
                        await interaction.response.send_message(ephemeral=True,embed=discord.Embed(title="Your Cashback", description=f"Balance - **{cachback}** RC", colour=discord.Color.blue()))
                    else:
                        await interaction.response.send_message(ephemeral=True,embed=discord.Embed(title="Your Cashback", description=f"In order to receive cashback, you must make at least 1 order", colour=discord.Color.blue()))
                except Exception as e:
                    print(f"bttn ERROR [MY CACHBACK] - {e}")
            case ["about", "cashback"]:
                try:
                    embed = discord.Embed(title="About Cashback", description="""
    What is cashback?
    When you buy something, you get 2% of the amount of your order to your cashback balance. This means that cashback is a way to reduce the price of future orders.
    After confirming the order, you will be credited with points in the form of RC currency (2% of the payment amount), in the future you will be able to use your RC in the order as a cashback to reduce its price.
    1 **RC** = 1 **$**
    cashback can only be used once per order (no more than 20% of the total amount of the order, and after using the cashback, N points will be deducted from your balance
    """, colour=discord.Color.blue())
                    embed.set_image(url="https://lh3.googleusercontent.com/fife/AAbDypCOySy6EFqL-ZfJ9TOM2rPcTuim7V0Q_mSBYpFJj8N0zoBSeJsGMP4oAB6E1xpbdd3jTOz0yt-EHCgqd-69LUO59DuRnKd6bbEE6VByKJRm8GyBWChArAnFtc8zYyoTzvt99G_YJQgV2M-GSyds12sLma3C3RNGXzSCmntsGZkHFP-50m7_SEx3GCm4IFlUBWFed7s9gTcwXHffRNlWTmfUIUx_YtO9aVKL_hmfn5xVXbYS_5cSzuAm8cdr7zVBwpkXkwSqsSv4AbRHTeE7x0pUUgx1rgOgfQVWAYPeHvmRQtUuvvXuGQKIso69YTMPGrd7M9qiGSvyLmZK1ChARrMi6FQu7m5h1qYJAsHX5EP89d9te5GOYYrtyChKqJnnTb_IM8WJqZhf46G9ks3M0N-XV-VfanE35lLftSN4xD-wEBSenOuEj97p1PJgaqj24bte4uGcB_uQefYSd7eTRbYE8sFVLBlzfgftJO9ufWvUC2MjrBGJmXlJlxy9oW9TYcgnz2G1vIL8mo94ImjGajT2JteN6x2gDhTFRLXbct-Ti7r44ybP53L2g3lfzbb6JwKxSGNAQmvekH_5cIIwsIOYogT8MXkDdsyAjH5CPGlBcE1okKqG13SC9vToI470CSgwNGw-S4TxaVFHAlHJYi-I8A7Tun6JltDn4jrpQ4F6dk0yGNRyYFaq1olD8tB1W63B9-yyUGvAAm8_F4_YmfDtexhkyPfm3l5Ndg2r4-dmEz4CqXgsULdYtttulzEp-A4x0EviJtMeNvMdW-zZkr5V5OU-44W-EQcc5HdNyyuojH1Knaf-5y6TV1p4h_usu-yLRIpJx69lckGt04yhe7ukWBYoUDeCrxKuhheoxqAmrSzWDBfPVHUVyYVaqXQfd_PZ7h0AYASv5bZwvPNxJTayI-aAoMsSzoNj0bXjpdtkOJdl0N_LL-ajjkM_-aaDnYi6daiCT05iPH-bagO_TCkdaCZT9B-LoIclGUypapShFyhZP1DchCx4YYnscZAofMGtj6fLyZdCGTFkrM1PHkoDN-DNqD-pD9m8eV4kJKyOIYQjFh8ETLqvcPsG70upI1H6IjQHPVkTZSM7D5Zniu0XKDbyVrgWqWSXZ3_QQGKJq-dK71QoDBg1DnQHcICBVFiBVLOCOVUz8vxvNAuu_BkrTlbRPAO-6D41Tlo3_NK7_9d2-XsyLuduD_JSnMF-gBCReOROXmivv7CZnVQKXmCYqHNcs0BxBAuNCRFcP9m2lKDHgLy0zV_5Xs3trBjYu-Ie_QvNdVnymGslbZK4rf498Ekm1mz4K5jRn392FmfCE9HvUX7RlCI1Bv_7oF8TTxnOvZoiJdannDXnJfE=w1868-h938")
                    await interaction.response.send_message(ephemeral=True,embed=embed)
                except Exception as e:
                    print(f"bttn ERROR [ABOUT CASHBACK] - {e}") 
            case ["support"]:
                modalSupport = modals.SupportModal()
                modalSupport.admin_channel = bot.get_channel(admin_chn_id)
                modalSupport.db = db
                await interaction.response.send_modal(modalSupport)

            case ["emoji", emoji]:
                await interaction.response.defer()
                await interaction.user.add_roles(get(interaction.guild.roles, id=config.roles.get(emoji)))

            #--------------ADMIN-PANEL------------------#
            case ["all", "codes"]:
                await AdminFunctions.all_codes(interaction, bot, db)
            case ["give", "answer", user_id]:
                await interaction.message.edit(view=View().add_item(Button(label="Ok", custom_id="ok")))
                await interaction.response.send_message(embed=discord.Embed(
                    title="Answer",
                    description=f"Give your answer",
                    colour=discord.Color.greyple()))
                answer = await bot.wait_for("message", check=lambda i:i.channel.id == interaction.channel_id and interaction.user.id == i.author.id)
                await interaction.delete_original_response()
                db.sqlite(f"UPDATE Questions SET answer = '{answer.content}' WHERE answer IS NULL AND user_id = {user_id}")
                description = f"**To <@{user_id}>** :"
                await answer.delete()
                for question, answer in db.sqlite(f"SELECT question, answer FROM Questions WHERE user_id = {user_id}"):
                    description += f"\n\n**Question** :\n{question}\n\n**Answer** :\n{answer}"
                member = await interaction.guild.fetch_member(user_id)
                view = View()
                view.add_item(Button(style=ButtonStyle.green, label="Yes", emoji="✅", custom_id='confirm_answer'))
                view.add_item(Button(label="No", emoji="❌", custom_id="not_confirm_answer"))
                try:
                    await member.send(embed=discord.Embed(title="Answer", description=description + '\n\nIs your question resolved?', colour=discord.Color.blurple()),
                    view=view)
                except Exception:
                    pass

            case ["add", "vtuber"]:
                await AdminFunctions.add_vtuber(interaction, bot, db, yt)
            case ["create", "news"]:
                await interaction.response.send_modal(modals.SendNews())
            case ["change", "cashback"]:
                await AdminFunctions.edit_cashback(interaction,bot,db)
            case ["create", "promocode"]:
                view=View()
                view.add_item(Button(label="Mixing", custom_id="Mixing", row=1))
                view.add_item(Button(label="Instrumentals", custom_id="Instrumentals", row=1))
                view.add_item(Button(label="Tuning/Timing", custom_id="Tuning/Timing", row=2))
                view.add_item(Button(label="Producing", custom_id="Producing", row=2))
                view.add_item(Button(label="BGM", custom_id="BGM", row=2))
                view.add_item(Button(label="All", custom_id="all",row=2))

                msg = await interaction.response.send_message(
                    embed=discord.Embed(title="Select a service category",description=f"Selecet a service category", colour=discord.Color.blue()),
                    view=view,
                )

                response = await bot.wait_for("interaction", check=lambda i:i.user.id == interaction.user.id and i.channel.id == interaction.channel_id)
                category = response.data.get("custom_id", None)

                modal = modals.CreatePromocode()
                modal.db = db
                modal.category = category
                await interaction.delete_original_response()
                await response.response.send_modal(modal)
            case ["delete", "promocode"]:
                await AdminFunctions.delete_promo(interaction, bot, db)
            case ["edit", "promocode"]:
                await AdminFunctions.edit_promocode(interaction, bot, db)
            case ["send", "order"]:
                await AdminFunctions.send_order(interaction, bot, db)
            case ["show", "all", "confirmed", "orders"]:
                await interaction.response.send_message("The command in dev")
                #await interaction.response.defer()
                #view = View()
                #view.add_item(Select(placeholder="Select a service category",options=[
                #    SelectOption(label="Mixing", value="Mixing"),
                #    SelectOption(label="Instrumentals", value="Instrumentals"),
                #    SelectOption(label="Tuning/Timing", value="Tuning/Timing"),
                #    SelectOption(label="Producing", value="Producing")
                #]))
                #msg = await interaction.channel.send(
                #    embed=discord.Embed(title="Category",description="Select a service category", colour=discord.Color.blue()),
                #    view=view, 
                #)
                #a = ("Mixing", "Instrumentals", "Tuning/Timing", "Producing")
                #resp = await bot.wait_for("interaction", check=lambda i: i.data.get('values')[0] in a and i.channel.id == interaction.channel_id and interaction.user.id == i.user.id)
                #service = resp.data.get('values')[0]
                #await resp.response.defer()
                #desc = ""
                #for user_id, url, isActive in db.sqlite(f"SELECT user_id, url, isActive FROM ConfirmedOrders WHERE service = '{service}'"):
                #    desc += f"**Client** : <@{user_id}>\n**Status** : {'🟢 Active' if bool(isActive) else '🔘 Closed'}\n**Confirmed link** : {url}\n\n"
                #await msg.edit(embed=discord.Embed(title=f"Service **{service.upper()}**",description=desc, colour=discord.Color.blue()),view=View())

            #----------------HELPS----------------------#
            
            case ["edit", "promocode", category, promocode, percent, user_id]:
                newOwner=await bot.fetch_user(int(user_id))
                db.sqlite(f"UPDATE Promocodes SET percent = {percent}, Owner = '{newOwner}' WHERE TypeService = '{category}' AND Name = '{promocode}'")
                await interaction.response.edit_message(embed=discord.Embed(title="Great", colour=discord.Color.greyple()), view=View().add_item(Button(label="Ok", custom_id="ok")))
            case ["send","news"]:
                newsChannel = bot.get_channel(964881949950885938)
                await newsChannel.send(embed=interaction.message.embeds[0])
                await interaction.response.edit_message(embed=discord.Embed(
                    title="Great",
                    description=f"The news was sent to channel {newsChannel.mention}",
                    colour=discord.Color.green()
                ), view=View().add_item(Button(label="Ok", custom_id="ok")))          
            case ["change", "cashback", newCashback, user_id]:
                await interaction.response.edit_message(embed=discord.Embed(title="Great", colour=discord.Color.green()), view=View().add_item(Button(label="Ok", custom_id="ok")))
                db.sqlite(f"UPDATE Clients SET Scores = {newCashback} WHERE user_id = {user_id}")
                try:
                    user = await bot.fetch_user(user_id)
                    await user.send(f"Your cashback has been changed. New balance: {newCashback}")
                except Exception as E:
                    print(str(E))
            case ["delete", "promo", category, promocode]:
                db.sqlite(f"DELETE FROM Promocodes WHERE TypeService = '{category}' AND Name = '{promocode}'")
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        title="Great",
                        colour=discord.Color.greyple()),
                    view=View().add_item(Button(style=ButtonStyle.red, label="Ok", custom_id="ok")))

            case ["enter", "edits"]:
                await interaction.response.defer()
                await interaction.channel.send(embed=discord.Embed(title="Comment", description="Enter your comment", colour=discord.Color.blue()))
                
                await interaction.channel.set_permissions(interaction.user, send_messages = True)
                try:
                    comment1 = await bot.wait_for("message", check=lambda i:i.channel.id == interaction.channel.id and i.author.id == interaction.user.id)
                except Exception as E:
                    print(str(E))
                await interaction.channel.set_permissions(interaction.user, send_messages = False)
                await interaction.channel.purge()
                comment = f'\nComment - {comment1.content}' if comment1.content != '' else ''
                view=View()
                view.add_item(Button(label="Ok", custom_id='ok'))
                msg1 = await bot.get_channel(admin_chn_id).send(interaction.user.mention, embed=discord.Embed(title="", description=f"The order has been sent for revision{comment}\n[ {interaction.channel.mention} ]", colour=discord.Color.red()),
                    view=view
                )
                await interaction.channel.send(embed=discord.Embed(title="The order has been sent for revision", description="Your order has been sent for revision\nExpect Execution", colour=discord.Color.blue()), view=View())
            case ["approve", "order"]:
                await interaction.response.defer()
                view=View()
                view.add_item(Button(label="Ok", custom_id='ok'))
                msg1 = await bot.get_channel(admin_chn_id).send(
                    interaction.user.mention,
                    embed=discord.Embed(
                        description=f"The order has been approved\n[ {interaction.channel.mention} ]",
                        colour=discord.Color.green()),
                    view=view
                )
                await interaction.message.edit(view=View())
                db.sqlite(f"DELETE FROM Orders WHERE user_id = {interaction.user.id} AND receipt_id = {interaction.channel.id}")
                db.sqlite(f"UPDATE ConfirmedOrders SET isActive = 0 WHERE user_name = '{str(interaction.user)}' AND receipt_id = {interaction.channel.id}")
                if db.sqlite(f"SELECT IsResponsed FROM Clients WHERE user_id = {interaction.user.id}")[0][0] == 0:
                    await functions.responseClient(response_chn_admin_id,response_chn_id,bot,interaction.channel, db)
                await msg1.delete()
                return


            case ["confirm", "answer"]:
                db.sqlite(f"DELETE FROM Questions WHERE user_id = {interaction.user.id}")
                await interaction.message.edit(view=View())
                view=View()
                view.add_item(Button(label="Ok", custom_id='ok'))
                await bot.get_channel(admin_chn_id).send(embed=discord.Embed(
                    title="Great",
                    description=f"{interaction.user.name} accepted the answer The question is closed !",
                    colour=discord.Color.green()),
                    view=view)
                await interaction.response.defer()
            case ["not", "confirm", "answer"]:
                await interaction.response.defer()
                await interaction.message.edit(view=View())
                msg = await interaction.user.send(embed=discord.Embed(
                    title="Enter your message",
                    description=f"{interaction.user.mention} Enter your message",
                    colour=discord.Color.blue()))
                try:
                    questionMsg = await bot.wait_for("message", check=lambda i:interaction.user.id == i.author.id and i.channel.id == interaction.channel_id, timeout=600)
                except asyncio.TimeoutError:
                    await msg.edit(embed=discord.Embed(title="Time is up", colour=discord.Color.red()))
                    await asyncio.sleep(7)
                    await msg.delete()
                    return
                view=View()
                view.add_item(Button(style=ButtonStyle.success, label="Answer", custom_id=f"give_answer_{interaction.user.id}"))
                await msg.edit(embed=discord.Embed(title="Expect answers", description="Expect responses from server administrators", colour=discord.Color.blue()))
                channel = bot.get_channel(admin_chn_id)
                date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                db.sqlite("INSERT INTO Questions VALUES ('{0}', '{1.content}', {1.author.id}, NULL)".format(str(questionMsg.author), questionMsg))
                messages = ""
                for question, answer in db.sqlite(f"SELECT question, answer FROM Questions WHERE user_id = {interaction.user.id}"):
                    messages += f"\n\n**Question** :\n{question}\n\n**Answer** :\n{answer}"
                await channel.send(embed=discord.Embed(
                    title="New Message",
                    description=f"**{interaction.user.mention} **:\n**Message history** : {messages}",
                    colour=discord.Color.blurple()
                ).set_footer(text=f"date : {date}"),
                view=view)
                await asyncio.sleep(10)
                await msg.delete()
            case ["ok"]:
                await interaction.message.delete()
                await interaction.response.defer()


@tasks.loop(seconds=30)
async def checkLiveStreamsTwitch():
    for id,streamer, place, status in db.sqlite("SELECT id,streamer, place, status FROM LiveStreams WHERE place = 'TWITCH'"):
        info = functions.CheckLiveStreamTwitch(streamer)
        match (info, status):
            case ("ERROR", _) | ("OFFLINE", "OFFLINE") | (None, "OFFLINE"):
                pass
            case ("OFFLINE", "LIVE"):
                db.sqlite(f"""UPDATE LiveStreams SET status = 'OFFLINE' WHERE streamer = '{streamer}' AND place = '{place}'""")
            case (_, "OFFLINE"):
                try:
                    db.sqlite(f"""UPDATE LiveStreams SET status = 'LIVE' WHERE streamer = '{streamer}' AND place = '{place}'""")
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

@tasks.loop(minutes=20)
async def checkLiveStreamsYouTube():
    for id,streamer, place, status in db.sqlite("SELECT id,streamer, place, status FROM LiveStreams WHERE place = 'YOUTUBE'"):
        info = functions.CheckLiveStreamYoutube(id)
        match (info, status):
            case ("ERROR", _) | ("OFFLINE", "OFFLINE") | (None, "OFFLINE"):
                pass
            case ("OFFLINE", "LIVE"):
                db.sqlite(f"""UPDATE LiveStreams SET status = 'OFFLINE' WHERE id = '{id}' AND place = '{place}'""")
            case (_, "OFFLINE"):
                try:
                    db.sqlite(f"""UPDATE LiveStreams SET status = 'LIVE' WHERE id = '{id}' AND place = '{place}'""")
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
   

if __name__ == '__main__':
    bot.run(config.TOKEN)