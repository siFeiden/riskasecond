import asyncio as aio
import json
import uuid


class Server(object):
    """Server handling communication with clients"""
    class Callbacks(object):
        """Contains methods for any type of event happening in the server"""
        async def player_connected(self, player):
            pass

        async def player_disconnected(self, player):
            pass

        async def message(self, player, payload):
            pass

    def __init__(self, server_callbacks, loop):
        self.server = None
        self.server_callbacks = server_callbacks
        self.loop = loop
        self.clients = {}

    def run(self, host, port):
        server_coro = aio.streams.start_server(
            self._accept_client,
            host, port,
            loop=self.loop
        )

        self.server = self.loop.run_until_complete(server_coro)

    def _accept_client(self, client_reader, client_writer):
        client_id = self.register_client(client_reader, client_writer)
        self.loop.create_task(self._handle_client(client_id))

    async def _handle_client(self, client_id):
        reader, _ = self.clients[client_id]

        # wait until registration finished
        await self.loop.create_task(
            self.server_callbacks.player_connected(client_id)
        )

        while True:
            data = await reader.readline()
            if not data:
                break

            data = data.decode('utf-8')
            self.handle_message(client_id, data.rstrip())

        self.unregister_client(client_id)
        self.loop.create_task(
            self.server_callbacks.player_disconnected(client_id)
        )

    def handle_message(self, client_id, message):
        self.loop.create_task(
            self.server_callbacks.message(client_id, message)
        )

    def register_client(self, client_reader, client_writer):
        new_id = uuid.uuid4()
        self.clients[new_id] = (client_reader, client_writer)

        return new_id

    def unregister_client(self, client_id):
        del self.clients[client_id]

    def send_message(self, client_id, message):
        self.loop.create_task(
            self._send_message(client_id, message)
        )

    async def _send_message(self, client_id, message):
        try:
            _, writer = self.clients[client_id]
        except KeyError:
            # client disconnected in the meantime, ignore failure on purpose
            pass
        else:
            serial = json.dumps(message.json()) + '\n'
            writer.write(serial.encode('utf-8'))
            await writer.drain()  # sth sth control flow
