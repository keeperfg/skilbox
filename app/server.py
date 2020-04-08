#
# Серверное приложение для соединений
#
import asyncio
from asyncio import transports
from time import sleep


class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport
    last_ten_messages: list = []  # 10 последних сообщений
    connected_users: list = []  # Список логинов, статическая

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):
        print(data)

        decoded = data.decode()

        if self.login is not None:
            self.send_message(decoded)
        else:
            if decoded.startswith("login:"):
                self.login = decoded.replace("login:", "").replace("\r\n", "")
                if self.login in ServerProtocol.connected_users:  # Проверяем, что пользователь с таким логином еще не вошел
                    self.transport.write(f"Логин занят {self.login}, попробуйте другой\r\n".encode())
                    sleep(3)
                    self.transport.close()  # Закрываем соединение
                else:
                    self.transport.write(
                        f"Привет, {self.login}!\r\n".encode()
                    )
                    ServerProtocol.connected_users.append(self.login)  # Формируем список пользователей сервера
                    self.send_history()  # Послать 10 последних сообщений новому пользователю
            else:
                self.transport.write("Неправильный логин\r\n".encode())

    # Послать 10 последних сообщений новому пользователю
    def send_history(self):
        for msg in ServerProtocol.last_ten_messages:
            self.transport.write(msg.encode())

    # Статическая функция ведения списка 10 сообщений
    @staticmethod
    def add_history(msg: str):
        if len(ServerProtocol.last_ten_messages) == 10:
            del ServerProtocol.last_ten_messages[0]
        ServerProtocol.last_ten_messages.append(msg)

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print("Пришел новый клиент")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Клиент вышел")

    def send_message(self, content: str):
        if content != '\r\n':  # Исключаем пустые строки
            message = f"{self.login}: {content}\r\n"
            ServerProtocol.add_history(message)  # Сохраняем сообщения
            for user in self.server.clients:
                if user.login is not None:  # Сообщения только для зарегистрированных пользователей
                    user.transport.write(message.encode())


class Server:
    clients: list

    def __init__(self):
        self.clients = []

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
