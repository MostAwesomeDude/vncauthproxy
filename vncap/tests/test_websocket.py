from twisted.trial import unittest

from vncap.websocket import (complete_hybi00, make_hybi00_frame,
                             parse_hybi00_frames, http_headers, make_accept,
                             mask, NORMAL, PING, PONG, parse_hybi06_frames)

class TestHTTPHeaders(unittest.TestCase):

    def test_single_header(self):
        raw = "Connection: Upgrade"
        headers = http_headers(raw)
        self.assertTrue("Connection" in headers)
        self.assertEqual(headers["Connection"], "Upgrade")

    def test_single_header_newline(self):
        raw = "Connection: Upgrade\r\n"
        headers = http_headers(raw)
        self.assertEqual(headers["Connection"], "Upgrade")

    def test_multiple_headers(self):
        raw = "Connection: Upgrade\r\nUpgrade: WebSocket"
        headers = http_headers(raw)
        self.assertEqual(headers["Connection"], "Upgrade")
        self.assertEqual(headers["Upgrade"], "WebSocket")

    def test_origin_colon(self):
        """
        Some headers have multiple colons in them.
        """

        raw = "Origin: http://example.com:8080"
        headers = http_headers(raw)
        self.assertEqual(headers["Origin"], "http://example.com:8080")

class TestKeys(unittest.TestCase):

    def test_make_accept_rfc(self):
        """
        Test ``make_accept()`` using the keys listed in the RFC for HyBi-07
        through HyBi-10.
        """

        key = "dGhlIHNhbXBsZSBub25jZQ=="

        self.assertEqual(make_accept(key), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_make_accept_wikipedia(self):
        """
        Test ``make_accept()`` using the keys listed on Wikipedia.
        """

        key = "x3JJHMbDL1EzLkh9GBhXDw=="

        self.assertEqual(make_accept(key), "HSmrc0sMlYUkAGmm5OPpG2HaGWk=")

class TestHyBi00(unittest.TestCase):

    def test_complete_hybi00_wikipedia(self):
        """
        Test complete_hybi00() using the keys listed on Wikipedia's WebSockets
        page.
        """

        headers = {
            "Sec-WebSocket-Key1": "4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2": "12998 5 Y3 1  .P00",
        }
        challenge = "^n:ds[4U"

        self.assertEqual(complete_hybi00(headers, challenge),
                         "8jKS'y:G*Co,Wxa-")

    def test_make_hybi00(self):
        """
        HyBi-00 frames are really, *really* simple.
        """

        self.assertEqual(make_hybi00_frame("Test!"), "\x00Test!\xff")

    def test_parse_hybi00_single(self):
        frame = "\x00Test\xff"

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], "Test")
        self.assertEqual(buf, "")

    def test_parse_hybi00_multiple(self):
        frame = "\x00Test\xff\x00Again\xff"

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0], "Test")
        self.assertEqual(frames[1], "Again")
        self.assertEqual(buf, "")

    def test_parse_hybi00_incomplete(self):
        frame = "\x00Test"

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 0)
        self.assertEqual(buf, "\x00Test")

    def test_parse_hybi00_garbage(self):
        frame = "trash\x00Test\xff"

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], "Test")
        self.assertEqual(buf, "")

    def test_socketio_crashers(self):
        """
        A series of snippets which crash other WebSockets implementations
        (specifically, Socket.IO) are harmless to this implementation.
        """

        frames = [
            """[{"length":1}]""",
            """{"messages":[{"length":1}]}""",
            "hello",
            "hello<script>alert(/xss/)</script>",
            "hello<img src=x:x onerror=alert(/xss.2/)>",
            "{",
            "~m~EVJLFDJP~",
        ]

        for frame in frames:
            prepared = make_hybi00_frame(frame)
            frames, buf = parse_hybi00_frames(prepared)

            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0], frame)
            self.assertEqual(buf, "")

class TestHyBi06Helpers(unittest.TestCase):
    """
    HyBi-06 is best understood as a large family of helper functions which
    work together, somewhat dysfunctionally, to produce a mediocre
    Thanksgiving every other year.
    """

    def test_mask_noop(self):
        key = "\x00\x00\x00\x00"
        self.assertEqual(mask("Test", key), "Test")

    def test_mask_noop_long(self):
        key = "\x00\x00\x00\x00"
        self.assertEqual(mask("LongTest", key), "LongTest")

    def test_parse_hybi06_unmasked_text(self):
        """
        From HyBi-10, 4.7.
        """

        frame = "\x81\x05Hello"
        frames, buf = parse_hybi06_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], ("Hello", NORMAL))
        self.assertEqual(buf, "")

    def test_parse_hybi06_masked_text(self):
        """
        From HyBi-10, 4.7.
        """

        frame = "\x81\x857\xfa!=\x7f\x9fMQX"
        frames, buf = parse_hybi06_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], ("Hello", NORMAL))
        self.assertEqual(buf, "")

    def test_parse_hybi06_unmasked_text_fragments(self):
        """
        We don't care about fragments. We are totally unfazed.

        From HyBi-10, 4.7.
        """

        frame = "\x01\x03Hel\x80\x02lo"
        frames, buf = parse_hybi06_frames(frame)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0], ("Hel", NORMAL))
        self.assertEqual(frames[1], ("lo", NORMAL))
        self.assertEqual(buf, "")

    def test_parse_hybi06_ping(self):
        """
        From HyBi-10, 4.7.
        """

        frame = "\x89\x05Hello"
        frames, buf = parse_hybi06_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], ("Hello", PING))
        self.assertEqual(buf, "")

    def test_parse_hybi06_pong(self):
        """
        From HyBi-10, 4.7.
        """

        frame = "\x8a\x05Hello"
        frames, buf = parse_hybi06_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], ("Hello", PONG))
        self.assertEqual(buf, "")
