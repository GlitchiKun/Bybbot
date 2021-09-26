from swag.db import Currency
from swag.errors import (
    CagnotteNameAlreadyExist,
    CagnotteDestructionForbidden,
    CagnotteUnspecifiedException,
    NoCagnotteRegistered,
    NotEnoughMoneyInCagnotte,
    NotCagnotteManager,
)
from apscheduler.triggers.cron import CronTrigger
from decimal import Decimal, ROUND_DOWN
from arrow import utcnow
from discord import File

from .bank import (
    AlreadyMineToday,
    InvalidSwagValue,
    InvalidStyleValue,
    InvalidTimeZone,
    TimeZoneFieldLocked,
    NoAccountRegistered,
    AccountAlreadyExist,
    NotEnoughStyleInBalance,
    NotEnoughSwagInBalance,
    StyleStillBlocked,
    SwagBank,
    BLOCKING_TIME,
)
from .utils import (
    currency_to_str,
    mini_history_swag_message,
    update_forbes_classement,
    update_the_style,
)

from utils import (
    BACKUP_CHANNEL_ID,
    GUILD_ID_BOBBYCRATIE,
    format_number,
    get_guild_member_name,
    reaction_message_building,
)
from module import Module


class SwagClient(Module):
    def __init__(self, client, db_path) -> None:
        self.client = client
        print("Initialisation de la Banque Centrale du $wag...\n")
        self.swag_bank = SwagBank(db_path)
        self.the_swaggest = None
        self.last_update = None

    async def setup(self):
        print("Mise à jour du classement et des bonus de blocage\n\n")
        await update_forbes_classement(
            self.client.get_guild(GUILD_ID_BOBBYCRATIE), self, self.client
        )

    async def add_jobs(self, scheduler):
        # Programme la fonction update_the_style pour être lancée
        # toutes les heures.
        async def style_job():
            now = utcnow().replace(microsecond=0, second=0, minute=0)
            if self.last_update is None or self.last_update < now:
                self.last_update = now
                await update_the_style(self.client, self)

        scheduler.add_job(style_job, CronTrigger(hour="*"))

        # Programme la fonction une fonction pour envoyer la db sur le serveur discord de dev
        # tout les jours, à 6h
        async def backup_job():
            await self.client.get_channel(BACKUP_CHANNEL_ID).send(
                file=File(self.swag_bank.db_path)
            )

        scheduler.add_job(backup_job, CronTrigger(day="*", hour="6"))

    async def process(self, message):
        try:
            if message.content.startswith("!$wagdmin"):
                await self.execute_swagdmin_command(message)
            elif message.content.startswith("!$wag"):
                await self.execute_swag_command(message)
            elif message.content.startswith("!$tyle"):
                await self.execute_style_command(message)
            elif message.content.startswith("!€agnotte"):
                await self.execute_cagnotte_command(message)
        except NotEnoughSwagInBalance:
            await message.channel.send(
                f"{message.author.mention} ! Tu ne possèdes pas assez de $wag pour "
                "faire cette transaction, vérifie ton solde avec `!$wag solde`"
            )
        except InvalidSwagValue:
            await message.channel.send(
                f"{message.author.mention}, la valeur que tu as écrite est "
                "incorrecte, elle doit être supérieur à 0 et entière, car le "
                "$wag est **indivisible** !"
            )
        except AlreadyMineToday:
            await message.channel.send(
                f"Désolé {message.author.mention}, mais tu as déjà miné du $wag "
                "aujourd'hui 😮 ! Reviens donc demain !"
            )
        except StyleStillBlocked:
            await message.channel.send(
                f"{message.author.mention}, du $wag est déjà bloqué à ton compte "
                "chez $tyle Generator Inc. ! Attends leurs déblocage pour pouvoir "
                "en bloquer de nouveau !"
            )
        except NotEnoughStyleInBalance:
            await message.channel.send(
                f"{message.author.mention} ! Tu ne possèdes pas assez de $tyle "
                "pour faire cette transaction, vérifie ton solde avec "
                "`!$tyle solde`"
            )
        except InvalidStyleValue:
            await message.channel.send(
                f"{message.author.mention}, la valeur que tu as écrite est "
                "incorrecte, elle doit être supérieur à 0, car le $tyle est "
                "**toujours positif** !"
            )
        except NoAccountRegistered as e:
            await message.channel.send(
                f"<@{e.name}>, tu ne possèdes pas de compte chez $wagBank™ "
                "<:rip:817165391846703114> !\n\n"
                "Remédie à ce problème en lançant la commande `!$wag créer` "
                "et devient véritablement $wag 😎!"
            )
        except AccountAlreadyExist:
            await message.channel.send(
                f"{message.author.mention}, tu possèdes déjà un compte chez $wagBank™ !"
            )
        except InvalidTimeZone as e:
            await message.channel.send(
                f"{e.name}, n'est pas un nom de timezone valide !\n"
                "Vérifie le nom correct sur "
                "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones, "
                "à la colone `TZ database name`."
            )
        except TimeZoneFieldLocked as e:
            await message.channel.send(
                "Tu viens déjà de changer de timezone. Tu ne pourras effectuer "
                f"à nouveau cette opération qu'après le {e.date}. Cette mesure "
                "vise à empécher l'abus de minage, merci de ta compréhension.\n\n"
                "*L'abus de minage est dangereux pour la santé. À Miner avec "
                "modération. Ceci était un message de la Fédération Bobbyique du "
                "Minage*"
            )
        except NoCagnotteRegistered as e:
            await message.channel.send(
                f"Aucune €agnotte n°€{e.name} est active dans la $wagBank ! "
                f"{message.author.mention}, tu t'es sans doute trompé de numéro 🤨"
            )
        except CagnotteNameAlreadyExist:
            await message.channel.send(
                f"{message.author.mention}, une €agnotte porte déjà ce nom ! "
                "Je te conseille de choisir un autre nom avant que tout le monde "
                "soit complètement duper 🤦‍♂️"
            )
        except NotEnoughMoneyInCagnotte as e:
            await message.channel.send(
                f"{message.author.mention}, tu es en train de demander à la €agnotte €{e.id} "
                "une somme d'argent qu'elle n'a pas. Non mais tu n'as pas honte ? 😐"
            )
        except NotCagnotteManager:
            await message.channel.send(
                f"{message.author.mention}, tu ne fais pas partie des gestionnaires "
                "de cette €agnotte, tu ne peux donc pas manipuler son contenu 🤷‍♀️"
            )
        except CagnotteDestructionForbidden:
            await message.channel.send(
                f"**Ligne 340 des conditions générales d'utilisations des €agnottes :**\n\n"
                "*Il est formellement interdit de détruire une cagnotte qui n'est pas vidée "
                "de son contenu. C'est comme ça.*"
            )
        except CagnotteUnspecifiedException:
            await message.channel.send(
                f"{message.author.mention}, il manque l'identifiant de la €agnotte"
                " dans la commande (€3 par exemple) afin de pouvoir faire l'action que tu demandes."
            )

    async def execute_swag_command(self, message):
        command_swag = message.content.split()

        if "créer" in command_swag:
            user = message.author
            guild = message.guild
            self.swag_bank.add_user(user.id, guild.id)
            await message.channel.send(
                f"Bienvenue chez $wagBank™ {user.mention} !\n\n"
                "Tu peux maintenant miner du $wag avec la commande `!$wag miner` 💰"
            )

        elif "miner" in command_swag:
            user = message.author
            mining_booty = self.swag_bank.mine(user.id)
            await message.channel.send(
                f"⛏ {user.mention} a miné `{format_number(mining_booty)} $wag` !"
            )
            await update_forbes_classement(message.guild, self, self.client)

        elif "info" in command_swag:
            user = message.author
            user_infos = self.swag_bank.get_account_info(user.id)

            # TODO : Changer l'affichage pour avoir une affichage à la bonne heure,
            # et en français
            release_info = (
                f"-Date du déblocage sur $wag : {user_infos.unblocking_date}\n"
                if user_infos.blocked_swag != 0
                else ""
            )
            await message.channel.send(
                "```diff\n"
                f"Relevé de compte de {message.author.display_name}\n"
                f"-$wag : {format_number(user_infos.swag_balance)}\n"
                f"-$tyle : {format_number(user_infos.style_balance)}\n"
                f"-Taux de bloquage : {format_number(user_infos.style_rate)} %\n"
                "-$wag actuellement bloqué : "
                f"{format_number(user_infos.blocked_swag)}\n"
                f"-$tyle généré : {format_number(user_infos.pending_style)}\n"
                f"{release_info}"
                f"-Timezone du compte : {user_infos.timezone}"
                "```"
            )

        elif "historique" in command_swag:
            user = message.author
            user_account = self.swag_bank.get_account_info(user.id)
            history = list(reversed(self.swag_bank.get_history(user.id)))
            await message.channel.send(
                f"{user.mention}, voici l'historique de tes transactions de $wag :\n"
            )
            await reaction_message_building(
                self.client,
                history,
                message,
                mini_history_swag_message,
                self.swag_bank,
                user_account.timezone,
            )

        elif "bloquer" in command_swag:
            # Récupération de la valeur envoyé
            user = message.author
            try:
                value = int(
                    "".join(argent for argent in command_swag if argent.isnumeric())
                )
            except ValueError:
                raise InvalidSwagValue

            self.swag_bank.block_swag(user.id, value)

            await message.channel.send(
                f"{user.mention}, vous venez de bloquer "
                f"`{format_number(value)} $wag`, vous les "
                f"récupérerez dans **{BLOCKING_TIME} jours** à la même "
                "heure\n"
            )
            await update_forbes_classement(message.guild, self, self.client)

        elif "payer" in command_swag:
            # Récupération du destinataire
            destinataire = message.mentions
            if len(destinataire) != 1:
                await message.channel.send(
                    "Merci de mentionner un destinataire (@Bobby Machin) "
                    "pour lui donner de ton $wag !"
                )
                return
            destinataire = destinataire[0]

            giver = message.author
            recipient = destinataire

            # Récupération de la valeur envoyé
            try:
                value = int(
                    "".join(argent for argent in command_swag if argent.isnumeric())
                )
            except ValueError:
                raise InvalidSwagValue

            # envoie du swag
            self.swag_bank.swag_transaction(giver.id, recipient.id, value)

            await message.channel.send(
                "Transaction effectué avec succès ! \n"
                "```ini\n"
                f"[{message.author.display_name}\t"
                f"{format_number(value)} $wag\t"
                f"-->\t{destinataire.display_name}]\n"
                "```"
            )
            await update_forbes_classement(message.guild, self, self.client)

        elif "timezone" in command_swag:
            timezone = command_swag[2]
            user = message.author

            date = self.swag_bank.set_timezone(user.id, timezone)
            await message.channel.send(
                f"Ta timezone est désormais {timezone} !\n"
                "Pour des raisons de sécurité, tu ne pourras plus changer celle-ci "
                f"avant {date}. Merci de ta compréhension."
            )

        else:
            # Si l'utilisateur se trompe de commande, ce message s'envoie par défaut
            await message.channel.send(
                f"{message.author.mention}, tu sembles perdu, "
                "voici les commandes que tu peux utiliser avec ton $wag :\n"
                "```HTTP\n"
                "!$wag créer ~~ Crée un compte chez $wagBank™\n"
                "!$wag info ~~ Voir ton solde et toutes les infos de ton compte \n"
                "!$wag miner ~~ Gagner du $wag gratuitement tout les jours\n"
                "!$wag payer [montant] [@destinataire] ~~ Envoie un *montant* "
                "de $wag au *destinataire* spécifié\n"
                "!$wag bloquer [montant] ~~ Bloque un *montant* de $wag pour "
                "générer du $tyle pendant quelques jours\n"
                "!$wag historique ~~ Visualiser l'ensemble des transactions "
                "effectuées sur ton compte\n"
                "```"
            )
        await update_forbes_classement(message.guild, self, self.client)

    async def execute_style_command(self, message):
        command_style = message.content.split()
        if "bloquer" in command_style:
            # Récupération de la valeur envoyé
            user = message.author

            try:
                value = int(
                    "".join(argent for argent in command_style if argent.isnumeric())
                )
            except ValueError:
                raise InvalidSwagValue

            self.swag_bank.block_swag(user.id, value)

            await message.channel.send(
                f"{user.mention}, vous venez de bloquer "
                f"`{format_number(value)} $wag`, vous les "
                f"récupérerez dans **{BLOCKING_TIME} jours** à la même "
                "heure\n"
            )
            await update_forbes_classement(message.guild, self, self.client)

        elif "payer" in command_style:
            # Récupération du destinataire
            destinataire = message.mentions
            if len(destinataire) != 1:
                await message.channel.send(
                    "Merci de mentionner un destinataire (@Bobby Machin) pour "
                    "lui donner de ton $tyle !"
                )
                return
            destinataire = destinataire[0]

            giver = message.author
            recipient = destinataire

            # Récupération de la valeur envoyé
            try:
                value = Decimal(
                    "".join(
                        argent
                        for argent in command_style
                        if argent.replace(".", "").replace(",", "").isnumeric()
                    )
                ).quantize(Decimal(".0001"), rounding=ROUND_DOWN)
            except ValueError:
                raise InvalidStyleValue

            # envoie du style
            self.swag_bank.style_transaction(giver.id, recipient.id, value)

            await message.channel.send(
                "Transaction effectué avec succès ! \n"
                "```ini\n"
                f"[{message.author.display_name}\t"
                f"{format_number(value)} $tyle\t"
                f"-->\t{destinataire.display_name}]\n"
                "```"
            )
            await update_forbes_classement(message.guild, self, self.client)

        else:
            await message.channel.send(
                f"{message.author.mention}, tu sembles perdu, voici les "
                "commandes que tu peux utiliser avec en relation avec ton "
                "$tyle :\n"
                "```HTTP\n"
                "!$tyle payer [montant] [@destinataire] ~~ Envoie un *montant* "
                "de $tyle au *destinataire* spécifié\n"
                "!$tyle bloquer [montant] ~~ Bloque un *montant* de $wag pour "
                "générer du $tyle pendant quelques jours\n"
                "```"
            )

    async def execute_swagdmin_command(self, message):
        user = message.author
        guild = message.guild

        if not user.guild_permissions.administrator:
            return

        command = message.content.split()
        if "timezone" in command:
            timezone = command[2]

            self.swag_bank.set_guild_timezone(guild.id, timezone)
            await message.channel.send(
                f"La timezone par défaut du serveur est désormais {timezone}.\n"
                "Les futurs comptes SwagBank créés sur ce serveur seront "
                "configurés pour utiliser cette timezone par défaut."
            )

        elif "jobs" in command:
            await update_the_style(self.client, self)

        else:
            await message.channel.send(
                f"{message.author.mention}, tu sembles perdu, voici les "
                "commandes administrateur que tu peux utiliser avec en relation "
                "avec le $wag\n"
                "```HTTP\n"
                "!$wagdmin timezone [timezone] ~~ Configure la timezone par défaut "
                "du serveur\n"
                "```"
            )

    async def execute_cagnotte_command(self, message):
        def get_cagnotte_idx_from_command(splited_command):
            try:
                cagnotte_idx = int(
                    [
                        identifiant[1:]
                        for identifiant in splited_command
                        if identifiant.startswith("€") and identifiant[1:].isnumeric()
                    ][0]
                )
                return cagnotte_idx
            except (IndexError):
                raise CagnotteUnspecifiedException

        message_command = message.content
        splited_command = message_command.split()

        if "créer $wag" in message_command:
            cagnotte_name = " ".join(splited_command[3:])
            if len(cagnotte_name) == 0:
                await message.channel.send(
                    "Merci de mentionner un nom pour ta €agnotte."
                )
                return
            new_cagnotte_idx = self.swag_bank.create_cagnotte(
                cagnotte_name, Currency.SWAG, message.author.id
            )

            cagnotte_info = self.swag_bank.swagdb.get_cagnotte(
                new_cagnotte_idx
            ).get_info()
            await message.channel.send(
                f"{message.author.mention} vient de créer une €agnotte de $wag nommée **« {cagnotte_name} »**. "
                f"Son identifiant est le €{cagnotte_info.id}"
            )

            await update_forbes_classement(message.guild, self, self.client)

        elif "créer $tyle" in message_command:
            cagnotte_name = " ".join(splited_command[3:])
            if len(cagnotte_name) == 0:
                await message.channel.send(
                    "Merci de mentionner un nom pour ta €agnotte."
                )
                return
            new_cagnotte_idx = self.swag_bank.create_cagnotte(
                cagnotte_name, Currency.STYLE, message.author.id
            )

            cagnotte_info = self.swag_bank.swagdb.get_cagnotte(
                new_cagnotte_idx
            ).get_info()
            await message.channel.send(
                f"{message.author.mention} vient de créer une €agnotte de $tyle nommée **« {cagnotte_name} »**. "
                f"Son identifiant est le €{cagnotte_info.id}"
            )
            await update_forbes_classement(message.guild, self, self.client)

        elif "créer" in splited_command:
            await message.channel.send(
                "Merci de mentionner le type de monnaie de la €agnotte "
                "après le mot clef **créer**"
            )

        # À partir d'ici, toutes les commandes doivent impérativement passer l'identifiant de €agnotte (sous forme de €n)

        elif "info" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)
            await message.channel.send(
                f"Voici les informations de la €agnotte €{cagnotte_idx}\n"
                "```\n"
                f"Nom de €agnotte : {cagnotte_info.name}\n"
                f"Type de €agnotte : {currency_to_str(cagnotte_info.currency)}\n"
                f"Montant de la €agnotte : {format_number(cagnotte_info.balance)} {currency_to_str(cagnotte_info.currency)}\n"
                f"Gestionnaire de la €agnotte : {[await get_guild_member_name(manager,message.guild,self.client) for manager in cagnotte_info.managers]}\n"
                f"Participants : {[await get_guild_member_name(participant,message.guild,self.client) for participant in cagnotte_info.participants]}\n"
                "```"
            )

        elif "historique" in splited_command:
            user = message.author
            user_account = self.swag_bank.get_account_info(user.id)

            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            history = list(reversed(self.swag_bank.get_cagnotte_history(cagnotte_idx)))

            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)
            await message.channel.send(
                f"{message.author.mention}, voici l'historique de tes transactions de la cagnotte **{cagnotte_info.name}** :\n"
            )
            await reaction_message_building(
                self.client,
                history,
                message,
                mini_history_swag_message,
                self.swag_bank,
                user_account.timezone,
            )

        elif "payer" in splited_command:

            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)

            if cagnotte_info.currency == Currency.SWAG:
                try:
                    value = int(
                        "".join(
                            argent for argent in splited_command if argent.isnumeric()
                        )
                    )
                except ValueError:
                    raise InvalidSwagValue

            elif cagnotte_info.currency == Currency.STYLE:
                try:
                    value = Decimal(
                        "".join(
                            argent
                            for argent in splited_command
                            if argent.replace(".", "").replace(",", "").isnumeric()
                        )
                    ).quantize(Decimal(".0001"), rounding=ROUND_DOWN)
                except ValueError:
                    raise InvalidStyleValue

            self.swag_bank.pay_to_cagnotte(message.author.id, cagnotte_idx, value)

            await message.channel.send(
                "Transaction effectuée avec succès ! \n"
                "```ini\n"
                f"[{message.author.display_name}\t"
                f"{format_number(value)} {currency_to_str(cagnotte_info.currency)}\t"
                f"-->\t€{cagnotte_idx} {cagnotte_info.name}]\n"
                "```"
            )
            await update_forbes_classement(message.guild, self, self.client)

        elif "donner" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)
            receiver = message.mentions
            if len(receiver) != 1:
                await message.channel.send(
                    "Merci de mentionner un destinataire (@Bobby Machin) pour "
                    "lui donner une partie de cette €agnotte !"
                )
                return
            receiver = receiver[0]

            if cagnotte_info.currency == Currency.SWAG:
                try:
                    value = int(
                        "".join(
                            argent for argent in splited_command if argent.isnumeric()
                        )
                    )
                except ValueError:
                    raise InvalidSwagValue

            elif cagnotte_info.currency == Currency.STYLE:
                try:
                    value = Decimal(
                        "".join(
                            argent
                            for argent in splited_command
                            if argent.replace(".", "").replace(",", "").isnumeric()
                        )
                    ).quantize(Decimal(".0001"), rounding=ROUND_DOWN)
                except ValueError:
                    raise InvalidStyleValue

            self.swag_bank.receive_from_cagnotte(
                cagnotte_idx, receiver.id, value, message.author.id
            )

            await message.channel.send(
                "Transaction effectuée avec succès ! \n"
                "```ini\n"
                f"[€{cagnotte_idx} {cagnotte_info.name}\t"
                f"{format_number(value)} {currency_to_str(cagnotte_info.currency)}\t"
                f"-->\t{receiver.display_name}]\n"
                "```"
            )

            await update_forbes_classement(message.guild, self, self.client)

        elif "partager" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            participants_id = [participant.id for participant in message.mentions]

            (participants_id, gain, winner_rest, rest,) = self.swag_bank.share_cagnotte(
                cagnotte_idx, participants_id, message.author.id
            )

            participants_str = []
            for participant_id in participants_id:
                user = message.guild.get_member(participant_id)
                if user == None:
                    participants_str.append(
                        await get_guild_member_name(
                            participant_id, message.guild, self.client
                        )
                    )
                else:
                    participants_str.append(user.mention)

            participants_mentions = ", ".join(participants_str)

            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)
            await message.channel.send(
                f"{participants_mentions} vous avez chacun récupéré `{format_number(gain)} {currency_to_str(cagnotte_info.currency)}`"
                f" de la cagnotte **{cagnotte_info.name}** 💸"
            )

            if winner_rest != None:
                user = message.guild.get_member(winner_rest)
                if user == None:
                    user_gagnant = await get_guild_member_name(
                        winner_rest, message.guild, self.client
                    )
                else:
                    user_gagnant = user.mention
                await message.channel.send(
                    f"{user_gagnant} récupère les `{format_number(rest)} {currency_to_str(cagnotte_info.currency)}` restants ! 🤑"
                )

            await update_forbes_classement(message.guild, self, self.client)

        elif "loto" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            participants_id = [participant.id for participant in message.mentions]

            gagnant, gain = self.swag_bank.lottery_cagnotte(
                cagnotte_idx, participants_id, message.author.id
            )

            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)
            await message.channel.send(
                f"{message.guild.get_member(gagnant).mention} vient de gagner l'intégralité de la €agnotte "
                f"€{cagnotte_idx} *{cagnotte_info.name}*, à savoir `{format_number(gain)} {currency_to_str(cagnotte_info.currency)}` ! 🎰"
            )

            await update_forbes_classement(message.guild, self, self.client)

        elif "renommer" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)

            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)

            new_name = [
                word
                for word in splited_command[1:]
                if word not in {f"€{cagnotte_idx}", "renommer"}
            ]

            new_name = " ".join(new_name)

            self.swag_bank.rename_cagnotte(cagnotte_idx, new_name, message.author.id)

            await message.channel.send(
                f'La €agnotte €{cagnotte_idx} anciennement nommé **"{cagnotte_info.name}"** s\'appelle maintenant **"{new_name}"**'
            )

            await update_forbes_classement(message.guild, self, self.client)

        elif "reset" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)
            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)

            self.swag_bank.reset_cagnotte_participants(cagnotte_idx, message.author.id)

            await message.channel.send(
                f'La liste des participants de la €agnotte €{cagnotte_idx} **"{cagnotte_info.name}"** a été remis à zéro 🔄'
            )

            await update_forbes_classement(message.guild, self, self.client)

        elif "détruire" in splited_command:
            cagnotte_idx = get_cagnotte_idx_from_command(splited_command)

            cagnotte_info = self.swag_bank.get_active_cagnotte_info(cagnotte_idx)
            self.swag_bank.destroy_cagnotte(cagnotte_idx, message.author.id)
            await message.channel.send(
                f"La €agnotte €{cagnotte_idx} *{cagnotte_info.name}* est maintenant détruite de ce plan de l'existence ❌"
            )
            await update_forbes_classement(message.guild, self, self.client)

        else:
            await message.channel.send(
                f"{message.author.mention}, tu as l'air perdu "
                "(c'est un peu normal, avec ces commandes pétées du cul...) 🙄\nVoici les commandes "
                "que tu peux utiliser avec les €agnottes :\n"
                "```HTTP\n"
                "!€agnotte créer [$wag/$tyle] [Nom_de_la_€agnotte] ~~ "
                "Permet de créer une nouvelle €agnotte, de $wag ou de $tyle "
                "avec le nom de son choix\n"
                "!€agnotte info €[n] ~~ Affiche des informations détaillés sur la €agnotte n\n"
                "!€agnotte historique €[n] ~~ Affiche les transactions en lien avec la €agnotte n\n"
                "!€agnotte payer €[n] [montant] ~~ fait don "
                "de la somme choisi à la €agnotte numéro €n\n"
                "⭐!€agnotte donner €[n] [montant] [@mention] ~~ donne à l'utilisateur mentionné "
                "un montant venant de la cagnotte\n"
                "⭐!€agnotte partager €[n] [@mention1 @mention2 ...] ~~ "
                "Partage l'intégralité de la €agnotte entre les utilisateurs mentionné. "
                "Si personne n'est mentionné, la €agnotte sera redistribué parmis les personnes ayant un compte à la $wagBank\n"
                "⭐!€agnotte loto €[n] [@mention1 @mention2 ...] ~~ "
                "Tire au sort parmis les utilisateurs mentionnés celui qui remportera l'intégralité "
                "de la €agnotte. Si personne n'est mentionné, le tirage au sort parmis les participants à la €agnotte\n"
                "⭐!€agnotte renommer €[n] [Nouveau nom] ~~ Change le nom de la €agnotte\n"
                "⭐!€agnotte reset €[n] ~~ Enlève tout les participants de la €agnotte de la liste des participants\n"
                "⭐!€agnotte détruire €[n] ~~ Détruit la €agnotte si elle est vide\n"
                "```\n"
                "*Seul le gestionnaire de la €agnotte peut faire les commandes précédées d'une  ⭐*"
            )
