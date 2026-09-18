import unittest
from pathlib import Path
from unittest.mock import patch

from k40core import usb_backend


class UsbBackendTests(unittest.TestCase):
    def tearDown(self):
        usb_backend.get_usb_backend.cache_clear()

    def test_bundled_legacy_backend_is_preferred(self):
        fake_path = Path("C:/package/libusb0.dll")
        legacy_backend = object()
        with patch.object(usb_backend, "_bundled_libusb0_path", return_value=fake_path), patch(
            "usb.backend.libusb0.get_backend", return_value=legacy_backend
        ) as get_legacy:
            self.assertIs(usb_backend.get_usb_backend(), legacy_backend)
        finder = get_legacy.call_args.kwargs["find_library"]
        self.assertEqual(finder("usb-0.1"), str(fake_path))

    def test_packaged_libusb1_is_the_fallback(self):
        modern_backend = object()
        with patch.object(usb_backend, "_bundled_libusb0_path", return_value=None), patch(
            "usb.backend.libusb0.get_backend", return_value=None
        ), patch(
            "libusb_package.get_libusb1_backend", return_value=modern_backend
        ):
            self.assertIs(usb_backend.get_usb_backend(), modern_backend)

    def test_find_passes_the_selected_backend(self):
        backend = object()
        device = object()
        with patch.object(usb_backend, "get_usb_backend", return_value=backend), patch(
            "usb.core.find", return_value=device
        ) as find:
            result = usb_backend.find_usb_device(idVendor=0x1A86, idProduct=0x5512)
        self.assertIs(result, device)
        find.assert_called_once_with(
            backend=backend, idVendor=0x1A86, idProduct=0x5512
        )


if __name__ == "__main__":
    unittest.main()
