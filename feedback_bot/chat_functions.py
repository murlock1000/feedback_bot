import logging
from collections import defaultdict
from typing import List, Union, Dict, Iterator

from commonmark import commonmark
# noinspection PyPackageRequirements
from nio import (
    SendRetryError,
    RoomSendResponse,
    RoomSendError,
    LocalProtocolError,
    AsyncClient,
    RoomCreateResponse,
    RoomCreateError,
    RoomPreset,
    RoomVisibility,
    RoomInviteError,
    RoomInviteResponse, RoomKickResponse, RoomKickError, MatrixRoom, RoomAvatarEvent,
    ToDeviceMessage
)
from nio.crypto import OlmDevice, InboundGroupSession, Session
from feedback_bot.utils import get_room_id, with_ratelimit

logger = logging.getLogger(__name__)

async def send_text_to_room(
    client: AsyncClient, room: str, message: str, notice: bool = True, markdown_convert: bool = True,
    reply_to_event_id: str = None, replaces_event_id: str = None,
) -> Union[RoomSendResponse, RoomSendError, str]:
    """Send text to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room (str): The ID or alias of the room to send the message to

        message (str): The message content

        notice (bool): Whether the message should be sent with an "m.notice" message type
            (will not ping users)

        markdown_convert (bool): Whether to convert the message content to markdown.
            Defaults to true.

        reply_to_event_id (str): Optional event ID that this message is a reply to.

        replaces_event_id (str): Optional event ID that this message replaces.
    """
    try:
        room_id = await get_room_id(client, room, logger)
    except ValueError as ex:
        return str(ex)

    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = commonmark(message)

    if replaces_event_id:
        content["m.relates_to"] = {
            "rel_type": "m.replace",
            "event_id": replaces_event_id,
        }
        content["m.new_content"] = {
            "msgtype": msgtype,
            "format": "org.matrix.custom.html",
            "body": message,
        }
        if markdown_convert:
            content["m.new_content"]["formatted_body"] = commonmark(message)
    # We don't store the original message content so cannot provide the fallback, unfortunately
    elif reply_to_event_id:
        content["m.relates_to"] = {
            "m.in_reply_to": {
                "event_id": reply_to_event_id,
            },
        }

    try:
        return await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
    except (LocalProtocolError, SendRetryError) as ex:
        logger.exception(f"Unable to send message response to {room_id}")
        return f"Failed to send message: {ex}"


async def send_room_redact(client: AsyncClient, room_id: str, redacts_event_id: str, reason:str):
    return await client.room_redact(
            room_id,
            redacts_event_id,
            reason,
        )

async def send_reaction(
    client: AsyncClient, room: str, event_id: str, reaction_key: str
) -> Union[RoomSendResponse, RoomSendError, str]:
    """Send reaction to event

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room (str): The ID or alias of the room to send the message to

        event_id (str): Event ID that this reaction is a reply to.

        reaction_key (str): The reaction symbol
    """
    try:
        room_id = await get_room_id(client, room, logger)
    except ValueError as ex:
        return str(ex)

    content = {
        "m.relates_to": {
            "rel_type": "m.annotation",
            "event_id": event_id,
            "key": reaction_key,
        }
    }

    try:
        return await client.room_send(
            room_id,
            "m.reaction",
            content,
            ignore_unverified_devices=True,
        )
    except (LocalProtocolError, SendRetryError) as ex:
        logger.exception(f"Unable to send reaction to {event_id}")
        return f"Failed to send reaction: {ex}"


async def send_media_to_room(
    client: AsyncClient, room: str, media_type: str, body: str, media_url: str = None,
    media_file: dict = None, media_info: dict = None, reply_to_event_id: str = None,
) -> Union[RoomSendResponse, RoomSendError, str]:
    """Send media to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room (str): The ID or alias of the room to send the message to

        media_type (str): The media type

        body (str): The media body

        media_url (str): The media url

        media_file (dict): The media metadata

        media_info (dict): The media url and metadata

        reply_to_event_id (str): Optional event ID that this message is a reply to.
    """
    try:
        room_id = await get_room_id(client, room, logger)
    except ValueError as ex:
        return str(ex)

    if not (media_url or media_file):
        logger.warning(f"Empty media url for room identifier: {room}")
        return "Empty media url"

    content = {
        "msgtype": media_type,
        "body": body,
    }

    if media_url:
        content.update({"url": media_url})

    if media_file:
        content.update({"file": media_file})

    if media_info:
        content.update({"info": media_info})

    # We don't store the original message content so cannot provide the fallback, unfortunately
    if reply_to_event_id:
        content["m.relates_to"] = {
            "m.in_reply_to": {
                "event_id": reply_to_event_id,
            },
        }

    try:
        return await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
    except (LocalProtocolError, SendRetryError) as ex:
        logger.exception(f"Unable to send media response to {room_id}")
        return f"Failed to send media: {ex}"


async def create_private_room(
        client: AsyncClient, mxid: str, roomname: str
    ) -> Union[RoomCreateResponse, RoomCreateError, RoomAvatarEvent]:

        """
        :param mxid: user id to create a DM for
        :param roomname: The DM room name
        :return: the Room Response from room_create()
        """
        resp = await with_ratelimit(client.room_create)(
                visibility=RoomVisibility.private,
                name=roomname,
                is_direct=True,
                preset=RoomPreset.private_chat,
                invite={mxid},
            )
        if isinstance(resp, RoomCreateResponse):
            logger.debug(f"Created a new DM for user {mxid} with roomID: {resp.room_id}")
        elif isinstance(resp, RoomCreateError):
            logger.exception(f"Failed to create a new DM for user {mxid} with error: {resp.status_code}")
        return resp

def is_user_in_room(room:MatrixRoom, mxid:str) -> bool:
    for user in room.users:
        if user == mxid:
            return True
    for user in room.invited_users:
        if user == mxid:
            return True
    return False
def is_room_private_msg(room: MatrixRoom, mxid: str) -> bool:
    if room.member_count == 2:
        return is_user_in_room(room, mxid)
    return False
def find_private_msg(client:AsyncClient, mxid: str) -> MatrixRoom:
    # Find if we already have a common room with user (Which is not a ticket room):
    msg_room = None
    for roomid in client.rooms:
        room = client.rooms[roomid]
        if is_room_private_msg(room, mxid):
            msg_room = room
            break

    if msg_room:
        logger.debug(f"Found existing DM for user {mxid} with roomID: {msg_room.room_id}")
    return msg_room

async def create_room(
        client: AsyncClient, roomname: str, invite:List[str] = []
) -> Union[RoomCreateResponse, RoomCreateError]:
    """
    :param roomname: The room name
    :return: the Room Response from room_create()
    """
    resp = await with_ratelimit(client.room_create)(
        name=roomname,
        invite=invite,
    )
    if isinstance(resp, RoomCreateResponse):
        logger.debug(f"Created a new room with roomID: {resp.room_id}")
    elif isinstance(resp, RoomCreateError):
        logger.exception(f"Failed to create a new room with error: {resp.status_code}")
    return resp
async def invite_to_room(
        client: AsyncClient, mxid: str, room_id: str
    ) -> Union[RoomInviteResponse, RoomInviteError]:

        """
        :param mxid: user id to invite
        :param roomname: The room name
        :return: the Room Response from room_create()
        """
        resp = await with_ratelimit(client.room_invite)(
                room_id=room_id,
                user_id=mxid,
            )
        if isinstance(resp, RoomInviteResponse):
            logger.debug(f"Invited user {mxid} to room: {room_id}")
        elif isinstance(resp, RoomInviteError):
            logger.exception(f"Failed to invite user {mxid} to room {room_id} with error: {resp.status_code}")
        return resp

## MSC3061: Sharing room keys for past messages - matrix-nio does not yet support sharing room keys, so this has been
## Implemented from scratch until proper library support comes out.
async def send_shared_history_keys(client:AsyncClient, room_id: str, user_ids:List[str]):

    if not client.olm:
        raise LocalProtocolError("End-to-end encryption disabled")

    # Get room
    room = client.rooms.get(room_id)
    if not room:
        logger.error("Unknown room. Not sharing decryption keys")
        return
    if not room.encrypted:
        logger.error("Room is unencrypted. Not sharing decryption keys")
        return

    # TODO: find way to fetch user devices from server.
    # Get user devices
    devices_by_user = {}
    for user_id in user_ids:
        devices_by_user[user_id] = client.device_store.active_user_devices(user_id)
    await send_shared_history_inbound_sessions(client, room, devices_by_user)

async def send_shared_history_inbound_sessions(client:AsyncClient, room:MatrixRoom, devices_by_user_iter: Dict[str, Iterator[OlmDevice]]):

    # Get stored InboundGroupSessions - currently storage does not differentiate between shareable and private, so we send all!!!.
    shared_history_sessions:defaultdict[str, defaultdict[str, InboundGroupSession]] = client.olm.inbound_group_store._entries[room.room_id]

    # Convert Iterator to list
    devices_by_user = {}
    for user, device_iter in devices_by_user_iter.items():
        devices_by_user[user] = list(device_iter)

    logger.debug(
        f"Sharing history of room {room.room_id} with users {devices_by_user.keys()}, {shared_history_sessions}")

    for sender_key, group_sessions in shared_history_sessions.items():
        for group_session in group_sessions.values():

            for user_id, devices in devices_by_user.items():
                for device in devices:
                    session = client.olm.session_store.get(device.curve25519)
                    if session is None:
                        logger.error(f"Session for user {user_id} device {device} is not available yet.")
                        continue
                    client.outgoing_to_device_messages.append(
                        _encrypt_forwarding_key(client, room.room_id, group_session, session, device)
                    )

                resp = await client.send_to_device_messages()
def _encrypt_forwarding_key(
        client: AsyncClient,
        room_id,  # type: str
        group_session,  # type: InboundGroupSession
        session,  # type: Session
        device,  # type: OlmDevice
):
    # type: (...) -> ToDeviceMessage
    """Encrypt a group session to be forwarded as a to-device message."""
    key_content = {
        "algorithm": client.olm._megolm_algorithm,
        "forwarding_curve25519_key_chain": group_session.forwarding_chain,
        "room_id": room_id,
        "sender_claimed_ed25519_key": group_session.ed25519,
        "sender_key": group_session.sender_key,
        "session_id": group_session.id,
        "session_key": group_session.export_session(
            group_session.first_known_index
        ),
        "chain_index": group_session.first_known_index,
        "org.matrix.msc3061.shared_history": True,
    }
    olm_dict = client.olm._olm_encrypt(
        session, device, "m.forwarded_room_key", key_content
    )
    return ToDeviceMessage(
        "m.room.encrypted", device.user_id, device.device_id, olm_dict
    )

async def kick_from_room(
        client: AsyncClient, mxid: str, room_id: str
) -> Union[RoomKickResponse , RoomKickError ]:
    """
    :param mxid: user id to kick
    :param roomname: The room name
    :return: the Room Response from room_create()
    """

    resp = await with_ratelimit(client.room_kick)(
        room_id=room_id,
        user_id=mxid,
    )
    if isinstance(resp, RoomKickResponse):
        logger.debug(f"kicked user {mxid} from room: {room_id}")
    elif isinstance(resp, RoomKickError):
        logger.exception(f"Failed to kick user {mxid} from room {room_id} with error: {resp.status_code}")
    return resp