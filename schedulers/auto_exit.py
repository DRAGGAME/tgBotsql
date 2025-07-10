from db.db import Sqlbase


async def auto_exit():
    sqlbase_auto_exit = Sqlbase()
    await sqlbase_auto_exit.connect()
    await sqlbase_auto_exit.update_state_admin(0)
    await sqlbase_auto_exit.close()
