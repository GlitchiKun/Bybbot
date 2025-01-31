import json
from typing import Dict
import cbor2
from attr import attrs, attrib
from arrow import Arrow
from disnake import TextChannel
import disnake
from swag.block import Block
from swag.blocks.system_blocks import AssetUploadBlock

from disnake import TextChannel
import disnake
from swag.block import Block


from .blockchain_parser import structure_block, unstructure_block
from .blockchain import SwagChain, json_converter


@attrs
class SyncedSwagChain(SwagChain):
    _id: int = attrib()
    _channel: TextChannel = attrib(init=False, default=None)
    _messages: Dict[Arrow, int] = attrib(init=False, default={})

    @classmethod
    async def from_channel(cls, bot_id: int, channel: TextChannel):
        synced_chain = cls([], bot_id)
        synced_chain._channel = channel
        synced_chain._messages = {}
        async for message in channel.history(limit=None, oldest_first=True):
            unstructured_block = json.loads(message.content)
            block = structure_block(unstructured_block)

            try:
                SwagChain.append(synced_chain, block)
                synced_chain._messages[block.timestamp] = message.id
                if isinstance(block, AssetUploadBlock):
                    # Mise à jour de la bibliothèque des assets
                    asset_url = message.attachments[0].url
                    synced_chain._assets[block.asset_key] = asset_url
            except Exception as e:
                print(f"\n\n\033[91mERREUR SUR LA BLOCKCHAIN\033[0m : {e}\n\n")
        return synced_chain

    async def append(self, block):
        SwagChain.append(self, block)

        # Envoie de l'asset si le block est une demande d'upload d'asset
        if isinstance(block, AssetUploadBlock):
            message = await self._channel.send(
                json.dumps(unstructure_block(block), default=json_converter),
                file=disnake.File(block.local_path),
            )
            # Mise à jour de la bibliothèque des assets
            asset_url = message.attachments[0].url
            self._assets[block.asset_key] = asset_url
        else:
            message = await self._channel.send(
                json.dumps(unstructure_block(block), default=json_converter)
            )

        self._messages[block.timestamp] = message.id
        # try:
        #     self._chain.append(block)
        #     await self._channel.send(json.dumps(unstructure_block(block)))
        # except AttributeError:
        #     raise ValueError(
        #         "Trying to call `append` on a `SyncedSwagChain` instance not "
        #         "bound to a TextChannel. Please use SyncedSwagChain.from_channel "
        #         "to create a bounded instance."
        #     )

    async def remove(self, block):
        SwagChain.remove(self, block)
        print(f"Delation of {block}")
        await self._channel.get_partial_message(
            self._messages.pop(block.timestamp)
        ).delete()

    async def save_backup(self):
        unstructured_blocks = []

        async for message in self._channel.history(limit=None, oldest_first=True):
            unstructured_blocks.append(json.loads(message.content))

        with open("swagchain.bk", "wb") as backup_file:
            cbor2.dump(unstructured_blocks, backup_file)
