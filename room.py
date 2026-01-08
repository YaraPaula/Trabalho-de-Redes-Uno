import threading
from game import UnoGame

class Room(threading.Thread):
    def __init__(self, room_id):
        super().__init__(daemon=True)
        self.room_id = room_id
        self.players = []
        self.nick = {}
        self.ready = set()
        self.game = None
        self.last_turn = None
        self.running = True

    def broadcast(self, msg):
        for p in list(self.players):
            try:
                p.sendall((msg + "\n").encode())
            except:
                self.remove_player(p)

    def add_player(self, conn):
        self.players.append(conn)
        self.nick[conn] = conn.nickname
        self.broadcast(f"PLAYER;{conn.nickname};JOINED")

    def remove_player(self, conn):
        if conn in self.players:
            self.players.remove(conn)
            self.ready.discard(conn)
            self.nick.pop(conn, None)
        self.broadcast(f"PLAYER;{conn.nickname};LEFT")

    def start_game(self):
        self.game = UnoGame(self.players)
        self.ready.clear()
        self.broadcast("GAME_STARTED")
        c, v = self.game.top_card()
        self.broadcast(f"TOP_CARD;{c};{v}")
        self._notify_turn()

    def _notify_turn(self):
        cur = self.game.current_player()
        if cur != self.last_turn:
            cur.sendall(b"YOUR_TURN\n")
            self.last_turn = cur

    def handle(self, conn, line):
        line = line.strip().upper()
        nick = self.nick.get(conn, "?")

        if line == "OK":
            if conn in self.ready:
                return 

            self.ready.add(conn)
            self.broadcast(f"PLAYER;{nick};READY")

            if self.game is None and len(self.players) >= 2 and len(self.ready) == len(self.players):
                self.start_game()

            return


        if not self.game:
            conn.sendall(b"ERROR;WAIT_FOR_GAME\n")
            return

        if line == "UNO":
            if self.game.call_uno(conn):
                self.broadcast(f"PLAYER;{nick};UNO")
            else:
                conn.sendall(b"ERROR;NO_UNO\n")
            return

        if conn != self.game.current_player():
            conn.sendall(b"ERROR;NOT_YOUR_TURN\n")
            return

        if line == "HAND":
            cards = ",".join(f"{c}-{v}" for c, v in self.game.hands[conn])
            conn.sendall(f"HAND;{cards}\n".encode())
            return

        if line == "DRAW":
            self.game.draw_card(conn)
            self.broadcast(f"PLAYER;{nick};DRAW")
            c, v = self.game.top_card()
            self.broadcast(f"TOP_CARD;{c};{v}")
            self._notify_turn()
            return

        parts = line.split()

        if parts[0] == "PLAY":
            if len(parts) != 3:
                conn.sendall(b"ERROR;USE PLAY <COR> <VALOR>\n")
                return

            if parts[1] == "WILD":
                conn.sendall(b"ERROR;USE WILD <COLOR|DRAW4> <COR>\n")
                return

            ok, result = self.game.play_card(conn, (parts[1], parts[2]))

            if not ok:
                conn.sendall(f"ERROR;{result}\n".encode())
                return

            if result == "WIN":
                self.broadcast(f"PLAYER;{nick};WIN")
                self.running = False

                for p in list(self.players):
                    try:
                        p.sendall(b"GAME_OVER\n")
                        p.close()
                    except:
                        pass

                self.players.clear()
                return

            if result == "UNO_WARNING":
                self.broadcast(f"PLAYER;{nick};UNO_WARNING")

            self.broadcast(f"PLAYER;{nick};PLAYED;{parts[1]};{parts[2]}")
            c, v = self.game.top_card()
            self.broadcast(f"TOP_CARD;{c};{v}")
            self._notify_turn()
            return

        if parts[0] == "WILD":
            if len(parts) != 3:
                conn.sendall(b"ERROR;USE WILD <COLOR|DRAW4> <COR>\n")
                return

            ok, result = self.game.play_card(
                conn,
                ("WILD", parts[1]),
                parts[2]
            )

            if not ok:
                conn.sendall(f"ERROR;{result}\n".encode())
                return

            if result == "WIN":
                self.broadcast(f"PLAYER;{nick};WIN")
                self.running = False

                for p in list(self.players):
                    try:
                        p.sendall(b"GAME_OVER\n")
                        p.close()
                    except:
                        pass

                self.players.clear()
                return

            if result == "UNO_WARNING":
                self.broadcast(f"PLAYER;{nick};UNO_WARNING")

            self.broadcast(f"PLAYER;{nick};WILD;{parts[1]};{parts[2]}")
            c, v = self.game.top_card()
            self.broadcast(f"TOP_CARD;{c};{v}")
            self._notify_turn()
            return

        conn.sendall(b"ERROR;UNKNOWN_COMMAND\n")
