import org.testng.annotations.Test;
import static org.testng.Assert.assertEquals;
import static org.testng.Assert.fail;

import java.io.ByteArrayInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;

public class IoUtilsTest {

    // Test cases for readBinaryLengthEncoding(InputStream in)

    @Test
    public void testReadBinaryLengthEncodingSmallValue() throws IOException {
        // Test case where firstByte <= 250
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 100 });
        long result = IoUtils.readBinaryLengthEncoding(in);
        assertEquals(result, 100L);
    }

    @Test
    public void testReadBinaryLengthEncodingNullValue() throws IOException {
        // Test case where firstByte == NULL_VALUE (0xfb)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) IoUtils.NULL_VALUE });
        long result = IoUtils.readBinaryLengthEncoding(in);
        assertEquals(result, -1L);
    }

    @Test
    public void testReadBinaryLengthEncodingUnsignedShort() throws IOException {
        // Test case where firstByte == 252, read unsigned short
        // Value: 500 (0x01F4) -> bytes: F4 01 (little endian)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 252, (byte) 0xF4, (byte) 0x01 });
        long result = IoUtils.readBinaryLengthEncoding(in);
        assertEquals(result, 500L);
    }

    @Test
    public void testReadBinaryLengthEncodingMediumInt() throws IOException {
        // Test case where firstByte == 253, read medium int
        // Value: 100000 (0x0186A0) -> bytes: A0 86 01 (little endian)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 253, (byte) 0xA0, (byte) 0x86, (byte) 0x01 });
        long result = IoUtils.readBinaryLengthEncoding(in);
        assertEquals(result, 100000L);
    }

    @Test
    public void testReadBinaryLengthEncodingLong() throws IOException {
        // Test case where firstByte == 254, read long
        // Value: 10000000000L (0x02540BE400L) -> bytes: 00 E4 0B 54 02 00 00 00 (little endian)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 254, (byte) 0x00, (byte) 0xE4, (byte) 0x0B, (byte) 0x54, (byte) 0x02, (byte) 0x00, (byte) 0x00, (byte) 0x00 });
        long result = IoUtils.readBinaryLengthEncoding(in);
        assertEquals(result, 10000000000L);
    }

    @Test
    public void testReadBinaryLengthEncodingLongNegativeResult() throws IOException {
        // Test case where firstByte == 254, and the resulting long is negative due to the 8th byte having MSB set
        // This should trigger the RuntimeException in IoUtils.readBinaryLengthEncoding
        // Value: -1, represented as 8 bytes 0xFF (little endian)
        InputStream in = new ByteArrayInputStream(new byte[]{
                (byte) 254,
                (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF,
                (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF
        });
        try {
            IoUtils.readBinaryLengthEncoding(in);
            fail("Expected RuntimeException for length too large to handle");
        } catch (RuntimeException e) {
            assertEquals(e.getMessage(), "Received length too large to handle");
        }
    }


    @Test
    public void testReadBinaryLengthEncodingIllegalStateException() throws IOException {
        // Test case for an unknown firstByte value (e.g., 251)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 251 });
        try {
            IoUtils.readBinaryLengthEncoding(in);
            fail("Expected IllegalStateException");
        } catch (IllegalStateException e) {
            assertEquals(e.getMessage(), "Recieved a length value we don't know how to handle");
        }
    }

    @Test
    public void testReadBinaryLengthEncodingEOFExceptionShort() {
        // Test case where stream ends prematurely for short
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 252, (byte) 0xF4 }); // Missing one byte for short
        try {
            IoUtils.readBinaryLengthEncoding(in);
            fail("Expected EOFException");
        } catch (IOException e) {
            // Check if it's EOFException or a subclass
            if (!(e instanceof EOFException)) {
                fail("Expected EOFException, but got " + e.getClass().getName());
            }
        }
    }

    @Test
    public void testReadBinaryLengthEncodingEOFExceptionMediumInt() {
        // Test case where stream ends prematurely for medium int
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 253, (byte) 0xA0, (byte) 0x86 }); // Missing one byte
        try {
            IoUtils.readBinaryLengthEncoding(in);
            fail("Expected EOFException");
        } catch (IOException e) {
            if (!(e instanceof EOFException)) {
                fail("Expected EOFException, but got " + e.getClass().getName());
            }
        }
    }

    @Test
    public void testReadBinaryLengthEncodingEOFExceptionLong() {
        // Test case where stream ends prematurely for long
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 254, (byte) 0x00, (byte) 0xE4, (byte) 0x0B, (byte) 0x54, (byte) 0x02, (byte) 0x00, (byte) 0x00 }); // Missing one byte
        try {
            IoUtils.readBinaryLengthEncoding(in);
            fail("Expected EOFException");
        } catch (IOException e) {
            if (!(e instanceof EOFException)) {
                fail("Expected EOFException, but got " + e.getClass().getName());
            }
        }
    }

    // Additional tests for other methods called by readBinaryLengthEncoding for comprehensive coverage

    @Test
    public void testSafeRead() throws IOException {
        InputStream in = new ByteArrayInputStream(new byte[]{ 10, 20 });
        assertEquals(IoUtils.safeRead(in), 10);
        assertEquals(IoUtils.safeRead(in), 20);
    }

    @Test(expectedExceptions = EOFException.class)
    public void testSafeReadEOF() throws IOException {
        InputStream in = new ByteArrayInputStream(new byte[]{});
        IoUtils.safeRead(in);
    }

    @Test
    public void testReadUnsignedShort() throws IOException {
        // 0x01F4 = 500
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0xF4, (byte) 0x01 });
        assertEquals(IoUtils.readUnsignedShort(in), 500);
    }

    @Test(expectedExceptions = EOFException.class)
    public void testReadUnsignedShortEOF() throws IOException {
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0xF4 });
        IoUtils.readUnsignedShort(in);
    }

    @Test
    public void testReadMediumIntPositive() throws IOException {
        // 0x0186A0 = 100000
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0xA0, (byte) 0x86, (byte) 0x01 });
        assertEquals(IoUtils.readMediumInt(in), 100000);
    }

    @Test
    public void testReadMediumIntNegative() throws IOException {
        // -1 (0xFFFFFFFF) represented as 3 bytes (0xFFFFFF)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0xFF, (byte) 0xFF, (byte) 0xFF });
        assertEquals(IoUtils.readMediumInt(in), -1);
    }

    @Test(expectedExceptions = EOFException.class)
    public void testReadMediumIntEOF() throws IOException {
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0xA0, (byte) 0x86 });
        IoUtils.readMediumInt(in);
    }

    @Test
    public void testReadLongPositive() throws IOException {
        // 10000000000L (0x02540BE400L) -> bytes: 00 E4 0B 54 02 00 00 00 (little endian)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0x00, (byte) 0xE4, (byte) 0x0B, (byte) 0x54, (byte) 0x02, (byte) 0x00, (byte) 0x00, (byte) 0x00 });
        assertEquals(IoUtils.readLong(in), 10000000000L);
    }

    @Test
    public void testReadLongNegative() throws IOException {
        // -1 (0xFFFFFFFFFFFFFFFFL) -> bytes: FF FF FF FF FF FF FF FF (little endian)
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF });
        assertEquals(IoUtils.readLong(in), -1L);
    }

    @Test(expectedExceptions = EOFException.class)
    public void testReadLongEOF() throws IOException {
        InputStream in = new ByteArrayInputStream(new byte[]{ (byte) 0x00, (byte) 0xE4, (byte) 0x0B, (byte) 0x54, (byte) 0x02, (byte) 0x00, (byte) 0x00 }); // Missing one byte
        IoUtils.readLong(in);
    }
}