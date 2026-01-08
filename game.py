import random

class UnoGame:
    COLORS = ["RED", "GREEN", "BLUE", "YELLOW"]
    VALUES = [str(n) for n in range(10)] + ["SKIP", "REVERSE", "DRAW2"]
    WILD_VALUES = ["COLOR", "DRAW4"]

    def __init__(self, players):
        self.players = players
        self.hands = {p: [] for p in players}
        self.turn = 0
        self.direction = 1
        self.deck = self._create_deck()
        self.discard = []

        self.uno_pending = None
        self.uno_pending_turn = None

        self._start()

    def _create_deck(self):
        deck = []
        for c in self.COLORS:
            for v in self.VALUES:
                deck += [(c, v), (c, v)]
        for w in self.WILD_VALUES:
            for _ in range(4):
                deck.append(("WILD", w))
        random.shuffle(deck)
        return deck

    def _draw(self):
        if not self.deck:
            self.deck = self.discard[:-1]
            random.shuffle(self.deck)
            self.discard = [self.discard[-1]]
        return self.deck.pop()

    def _start(self):
        for _ in range(7):
            for p in self.players:
                self.hands[p].append(self._draw())
        while True:
            c = self._draw()
            if c[0] != "WILD":
                self.discard.append(c)
                break
            self.deck.insert(0, c)

    def top_card(self):
        return self.discard[-1]

    def current_player(self):
        return self.players[self.turn]

    def next_turn(self, step=1):
        self.turn = (self.turn + step * self.direction) % len(self.players)

    def is_valid(self, card):
        tc, tv = self.top_card()
        c, v = card
        return c == "WILD" or c == tc or v == tv

    def draw_card(self, p):
        if p != self.current_player():
            return False
        self.hands[p].append(self._draw())
        self._check_uno_timeout()
        self.next_turn()
        return True

    def call_uno(self, p):
        if self.uno_pending == p:
            self.uno_pending = None
            self.uno_pending_turn = None
            return True
        return False

    def _check_uno_timeout(self):
        if self.uno_pending and self.turn != self.uno_pending_turn:
            p = self.uno_pending
            self.hands[p].append(self._draw())
            self.hands[p].append(self._draw())
            self.uno_pending = None
            self.uno_pending_turn = None
            return p
        return None

    def play_card(self, p, card, chosen_color=None):
        if p != self.current_player():
            return False, "NOT_YOUR_TURN"
        if card not in self.hands[p]:
            return False, "CARD_NOT_IN_HAND"
        if not self.is_valid(card):
            return False, "INVALID_CARD"

        self.hands[p].remove(card)
        color, value = card

        if color == "WILD":
            if not chosen_color:
                return False, "COLOR_REQUIRED"
            self.discard.append((chosen_color, value))
            if value == "DRAW4":
                self.next_turn()
                t = self.current_player()
                for _ in range(4):
                    self.hands[t].append(self._draw())
            self._check_uno_timeout()
            self.next_turn()
        else:
            self.discard.append(card)
            if value == "SKIP":
                self._check_uno_timeout()
                self.next_turn(2)
            elif value == "REVERSE":
                if len(self.players) == 2:
                    self._check_uno_timeout()
                    self.next_turn(2)
                else:
                    self.direction *= -1
                    self._check_uno_timeout()
                    self.next_turn()
            elif value == "DRAW2":
                self.next_turn()
                t = self.current_player()
                for _ in range(2):
                    self.hands[t].append(self._draw())
                self._check_uno_timeout()
                self.next_turn()
            else:
                self._check_uno_timeout()
                self.next_turn()

        if len(self.hands[p]) == 1:
            self.uno_pending = p
            self.uno_pending_turn = self.turn
            return True, "UNO_WARNING"

        if len(self.hands[p]) == 0:
            return True, "WIN"

        return True, "OK"
