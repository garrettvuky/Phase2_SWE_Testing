package org.adbcj.mysql.codec;

import org.junit.Test;
import static org.junit.Assert.*;

import java.io.ByteArrayInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;

public class IoUtilsTest {

    @Test
    public void testReadLengthCodedString_ShortString() throws IOException {
        String testString = "Hello";
        byte[] stringBytes = testString.getBytes("UTF-8");
        byte[] lengthByte = {(byte) stringBytes.length}; // Length 5

        ByteArrayInputStream in = new ByteArrayInputStream(concatenate(lengthByte, stringBytes));
        String result = IoUtils.readLengthCodedString(in, "UTF-8");
        assertEquals(testString, result);
    }

    @Test
    public void testReadLengthCodedString_NullValue() throws IOException {
        byte[] nullByte = {(byte) IoUtils.NULL_VALUE}; // 0xfb

        ByteArrayInputStream in = new ByteArrayInputStream(nullByte);
        String result = IoUtils.readLengthCodedString(in, "UTF-8");
        assertNull(result); // Should return null for NULL_VALUE
    }

    @Test
    public void testReadLengthCodedString_UnsignedShortLength() throws IOException {
        String testString = generateLongString(251); // Length 251, requires 2 bytes for length
        byte[] stringBytes = testString.getBytes("UTF-8");

        // Length 251 (0xfb), encoded as 0xfc, 0xfb, 0x00 for 2-byte length
        byte[] lengthBytes = {(byte) 252, (byte) 251, (byte) 0};

        ByteArrayInputStream in = new ByteArrayInputStream(concatenate(lengthBytes, stringBytes));
        String result = IoUtils.readLengthCodedString(in, "UTF-8");
        assertEquals(testString, result);
    }

    @Test
    public void testReadLengthCodedString_MediumIntLength() throws IOException {
        String testString = generateLongString(65536); // Length 65536, requires 3 bytes for length
        byte[] stringBytes = testString.getBytes("UTF-8");

        // Length 65536 (0x10000), encoded as 0xfd, 0x00, 0x00, 0x01 for 3-byte length
        byte[] lengthBytes = {(byte) 253, (byte) 0, (byte) 0, (byte) 1};

        ByteArrayInputStream in = new ByteArrayInputStream(concatenate(lengthBytes, stringBytes));
        String result = IoUtils.readLengthCodedString(in, "UTF-8");
        assertEquals(testString, result);
    }

    @Test
    public void testReadLengthCodedString_LongLength() throws IOException {
        String testString = generateLongString(100000); // Length 100000, requires 8 bytes for length
        byte[] stringBytes = testString.getBytes("UTF-8");

        // Length 100000 (0x000186a0), encoded as 0xfe, followed by 8 bytes for long
        byte[] lengthBytes = {
            (byte) 254,
            (byte) 0xa0, (byte) 0x86, (byte) 0x01, (byte) 0x00,
            (byte) 0x00, (byte) 0x00, (byte) 0x00, (byte) 0x00
        };

        ByteArrayInputStream in = new ByteArrayInputStream(concatenate(lengthBytes, stringBytes));
        String result = IoUtils.readLengthCodedString(in, "UTF-8");
        assertEquals(testString, result);
    }

    @Test
    public void testReadLengthCodedString_EmptyString() throws IOException {
        byte[] lengthByte = {(byte) 0}; // Length 0

        ByteArrayInputStream in = new ByteArrayInputStream(lengthByte);
        String result = IoUtils.readLengthCodedString(in, "UTF-8");
        assertEquals("", result);
    }

    @Test(expected = EOFException.class)
    public void testReadLengthCodedString_PrematureEOF_LengthByte() throws IOException {
        ByteArrayInputStream in = new ByteArrayInputStream(new byte[0]);
        IoUtils.readLengthCodedString(in, "UTF-8");
    }

    @Test(expected = IOException.class)
    public void testReadLengthCodedString_PrematureEOF_StringBytes() throws IOException {
        String testString = "Short";
        byte[] stringBytes = testString.getBytes("UTF-8");
        byte[] lengthByte = {(byte) (stringBytes.length + 5)}; // Claim a length longer than available bytes

        ByteArrayInputStream in = new ByteArrayInputStream(concatenate(lengthByte, stringBytes));
        IoUtils.readLengthCodedString(in, "UTF-8");
    }

    @Test
    public void testReadLengthCodedString_DifferentCharset() throws IOException {
        String testString = "Hello World æøå";
        String charsetName = "ISO-8859-1";
        byte[] stringBytes = testString.getBytes(charsetName);
        byte[] lengthByte = {(byte) stringBytes.length};

        ByteArrayInputStream in = new ByteArrayInputStream(concatenate(lengthByte, stringBytes));
        String result = IoUtils.readLengthCodedString(in, charsetName);
        assertEquals(testString, result);
    }
    
    // Helper method to concatenate byte arrays
    private byte[] concatenate(byte[] a, byte[] b) {
        byte[] result = new byte[a.length + b.length];
        System.arraycopy(a, 0, result, 0, a.length);
        System.arraycopy(b, 0, result, a.length, b.length);
        return result;
    }

    // Helper method to generate a long string for testing
    private String generateLongString(int length) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++) {
            sb.append((char) ('a' + (i % 26)));
        }
        return sb.toString();
    }
}