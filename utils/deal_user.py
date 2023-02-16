from telethon.tl.types import User


def format(user: User) -> dict:
    status = None
    if user.status is not None:
        status = user.status.to_dict()
    response = {"id": user.id,
                "is_self": user.is_self,
                "contact": user.contact,
                "mutual_contact": user.mutual_contact,
                "deleted": user.deleted,
                "bot": user.bot,
                "bot_chat_history": user.bot_chat_history,
                "bot_nochats": user.bot_nochats,
                "verified": user.verified,
                "restricted": user.restricted,
                "min": user.min,
                "bot_inline_geo": user.bot_inline_geo,
                "support": user.support,
                "scam": user.scam,
                "apply_min_photo": user.apply_min_photo,
                "fake": user.fake,
                "bot_attach_menu": user.bot_attach_menu,
                "premium": user.premium,
                "attach_menu_enabled": user.attach_menu_enabled,
                "access_hash": user.access_hash,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "status": status,
                "bot_info_version": user.bot_info_version,
                "bot_inline_placeholder": user.bot_inline_placeholder,
                "lang_code": user.lang_code}
    return response

