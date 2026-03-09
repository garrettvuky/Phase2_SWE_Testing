package org.semanticweb.yars.nx.dt;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;
import org.semanticweb.yars.nx.Literal;
import org.semanticweb.yars.nx.Resource;
import org.semanticweb.yars.nx.dt.binary.XsdBase64Binary;
import org.semanticweb.yars.nx.dt.binary.XsdHexBinary;
import org.semanticweb.yars.nx.dt.bool.XsdBoolean;
import org.semanticweb.yars.nx.dt.datetime.XsdDate;
import org.semanticweb.yars.nx.dt.datetime.XsdDateTime;
import org.semanticweb.yars.nx.dt.datetime.XsdDateTimeStamp;
import org.semanticweb.yars.nx.dt.datetime.XsdGDay;
import org.semanticweb.yars.nx.dt.datetime.XsdGMonth;
import org.semanticweb.yars.nx.dt.datetime.XsdGMonthDay;
import org.semanticweb.yars.nx.dt.datetime.XsdGYear;
import org.semanticweb.yars.nx.dt.datetime.XsdGYearMonth;
import org.semanticweb.yars.nx.dt.datetime.XsdTime;
import org.semanticweb.yars.nx.dt.numeric.XsdByte;
import org.semanticweb.yars.nx.dt.numeric.XsdDecimal;
import org.semanticweb.yars.nx.dt.numeric.XsdDouble;
import org.semanticweb.yars.nx.dt.numeric.XsdFloat;
import org.semanticweb.yars.nx.dt.numeric.XsdInt;
import org.semanticweb.yars.nx.dt.numeric.XsdInteger;
import org.semanticweb.yars.nx.dt.numeric.XsdLong;
import org.semanticweb.yars.nx.dt.numeric.XsdNegativeInteger;
import org.semanticweb.yars.nx.dt.numeric.XsdNonNegativeInteger;
import org.semanticweb.yars.nx.dt.numeric.XsdNonPositiveInteger;
import org.semanticweb.yars.nx.dt.numeric.XsdPositiveInteger;
import org.semanticweb.yars.nx.dt.numeric.XsdShort;
import org.semanticweb.yars.nx.dt.numeric.XsdUnsignedByte;
import org.semanticweb.yars.nx.dt.numeric.XsdUnsignedInt;
import org.semanticweb.yars.nx.dt.numeric.XsdUnsignedLong;
import org.semanticweb.yars.nx.dt.numeric.XsdUnsignedShort;
import org.semanticweb.yars.nx.dt.string.XsdLanguage;
import org.semanticweb.yars.nx.dt.string.XsdNCName;
import org.semanticweb.yars.nx.dt.string.XsdNMToken;
import org.semanticweb.yars.nx.dt.string.XsdName;
import org.semanticweb.yars.nx.dt.string.XsdNormalisedString;
import org.semanticweb.yars.nx.dt.string.XsdString;
import org.semanticweb.yars.nx.dt.string.XsdToken;
import org.semanticweb.yars.nx.dt.uri.XsdAnyURI;
import org.semanticweb.yars.nx.dt.xml.RdfXmlLiteral;
import org.semanticweb.yars.nx.namespace.RDF;
import org.semanticweb.yars.nx.namespace.XSD;
import org.semanticweb.yars.nx.parser.ParseException;

public class DatatypeFactoryTest {

    @Test
    public void testGetDatatypeFromLiteralXsdString() throws DatatypeParseException, ParseException {
        Literal literal = new Literal("testString", XSD.STRING);
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype(literal);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdString);
    }

    @Test
    public void testGetDatatypeFromLiteralPlainLiteral() throws DatatypeParseException, ParseException {
        Literal literal = new Literal("plainLiteral");
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype(literal);
        assertNull(dt);
    }

    @Test
    public void testGetDatatypeFromLiteralWithLangTag() throws DatatypeParseException, ParseException {
        Literal literal = new Literal("hello", "en");
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype(literal);
        assertNull(dt);
    }
    
    @Test
    public void testGetDatatypeFromLiteralRdfXmlLiteral() throws DatatypeParseException, ParseException {
        Literal literal = new Literal("<root>xml</root>", RDF.XMLLITERAL);
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype(literal);
        assertNotNull(dt);
        assertTrue(dt instanceof RdfXmlLiteral);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdString() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("testString", XSD.STRING);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdString);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdBooleanTrue() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("true", XSD.BOOLEAN);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdBoolean);
        assertTrue(((XsdBoolean) dt).getValue().booleanValue());
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdBooleanFalse() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("false", XSD.BOOLEAN);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdBoolean);
        assertTrue(!((XsdBoolean) dt).getValue().booleanValue());
    }

    @Test(expected = DatatypeParseException.class)
    public void testGetDatatypeFromLexAndDtXsdBooleanInvalid() throws DatatypeParseException {
        DatatypeFactory.getDatatype("notABoolean", XSD.BOOLEAN);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdInteger() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.INTEGER);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdInteger);
    }

    @Test(expected = DatatypeParseException.class)
    public void testGetDatatypeFromLexAndDtXsdIntegerInvalid() throws DatatypeParseException {
        DatatypeFactory.getDatatype("abc", XSD.INTEGER);
    }
    
    @Test
    public void testGetDatatypeFromLexAndDtXsdInt() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.INT);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdInt);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdLong() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("1234567890123", XSD.LONG);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdLong);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdShort() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.SHORT);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdShort);
    }
    
    @Test
    public void testGetDatatypeFromLexAndDtXsdByte() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.BYTE);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdByte);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdDecimal() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123.45", XSD.DECIMAL);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdDecimal);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdFloat() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("1.23E4", XSD.FLOAT);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdFloat);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdDouble() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("1.23E-4", XSD.DOUBLE);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdDouble);
    }
    
    @Test
    public void testGetDatatypeFromLexAndDtXsdDateTime() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("2023-01-01T12:00:00Z", XSD.DATETIME);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdDateTime);
    }
    
    @Test
    public void testGetDatatypeFromLexAndDtXsdDateTimeStamp() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("2023-01-01T12:00:00.123Z", XSD.DATETIMESTAMP);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdDateTimeStamp);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdDate() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("2023-01-01", XSD.DATE);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdDate);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdTime() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("12:00:00Z", XSD.TIME);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdTime);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdGYearMonth() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("2023-01", XSD.GYEARMONTH);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdGYearMonth);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdGYear() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("2023", XSD.GYEAR);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdGYear);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdGMonthDay() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("--01-01", XSD.GMONTHDAY);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdGMonthDay);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdGMonth() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("--01", XSD.GMONTH);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdGMonth);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdGDay() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("---01", XSD.GDAY);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdGDay);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdHexBinary() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("0FB7", XSD.HEXBINARY);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdHexBinary);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdBase64Binary() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("Zm9vYmFy", XSD.BASE64BINARY);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdBase64Binary);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdToken() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("a token", XSD.TOKEN);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdToken);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdNMToken() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("a-token", XSD.NMTOKEN);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdNMToken);
    }
    
    @Test
    public void testGetDatatypeFromLexAndDtXsdName() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("TestName", XSD.NAME);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdName);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdNCName() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("ncName", XSD.NCNAME);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdNCName);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdNonNegativeInteger() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.NONNEGATIVEINTEGER);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdNonNegativeInteger);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdPositiveInteger() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.POSITIVEINTEGER);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdPositiveInteger);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdNonPositiveInteger() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("-123", XSD.NONPOSITIVEINTEGER);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdNonPositiveInteger);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdNegativeInteger() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("-123", XSD.NEGATIVEINTEGER);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdNegativeInteger);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdNormalisedString() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("normalised string", XSD.NORMALIZEDSTRING);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdNormalisedString);
    }
    
    @Test
    public void testGetDatatypeFromLexAndDtXsdAnyURI() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("http://example.org/", XSD.ANYURI);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdAnyURI);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdLanguage() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("en-US", XSD.LANGUAGE);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdLanguage);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdUnsignedLong() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("12345", XSD.UNSIGNEDLONG);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdUnsignedLong);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdUnsignedInt() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.UNSIGNEDINT);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdUnsignedInt);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdUnsignedShort() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.UNSIGNEDSHORT);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdUnsignedShort);
    }

    @Test
    public void testGetDatatypeFromLexAndDtXsdUnsignedByte() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("123", XSD.UNSIGNEDBYTE);
        assertNotNull(dt);
        assertTrue(dt instanceof XsdUnsignedByte);
    }

    @Test
    public void testGetDatatypeFromLexAndDtRdfXmlLiteral() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("<root>xml</root>", RDF.XMLLITERAL);
        assertNotNull(dt);
        assertTrue(dt instanceof RdfXmlLiteral);
    }

    @Test
    public void testGetDatatypeFromLexAndDtUnsupportedDatatype() throws DatatypeParseException {
        Resource unsupportedDt = new Resource("http://example.org/unsupportedDatatype");
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("someValue", unsupportedDt);
        assertNull(dt);
    }

    @Test
    public void testGetDatatypeFromLexAndDtNullLexicalForm() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype(null, XSD.STRING);
        assertNull(dt);
    }

    @Test
    public void testGetDatatypeFromLexAndDtNullDatatype() throws DatatypeParseException {
        Datatype<? extends Object> dt = DatatypeFactory.getDatatype("testString", null);
        assertNull(dt);
    }
}
