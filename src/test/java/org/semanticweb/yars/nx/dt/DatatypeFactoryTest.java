package org.semanticweb.yars.nx.dt;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.semanticweb.yars.nx.Literal;
import org.semanticweb.yars.nx.Resource;
import org.semanticweb.yars.nx.dt.bool.XsdBoolean;
import org.semanticweb.yars.nx.dt.numeric.XsdInteger;
import org.semanticweb.yars.nx.dt.string.XsdString;
import org.semanticweb.yars.nx.dt.xml.RdfXmlLiteral;
import org.semanticweb.yars.nx.namespace.RDF;
import org.semanticweb.yars.nx.namespace.XSD;
import org.semanticweb.yars.nx.parser.ParseException;

public class DatatypeFactoryTest {

    @Test
    public void testGetStringDatatype() throws DatatypeParseException {
        Resource dt = XSD.STRING;
        String lex = "test string";
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNotNull(datatype);
        assertTrue(datatype instanceof XsdString);
    }

    @Test
    public void testGetBooleanDatatype() throws DatatypeParseException {
        Resource dt = XSD.BOOLEAN;
        String lex = "true";
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNotNull(datatype);
        assertTrue(datatype instanceof XsdBoolean);
    }

    @Test(expected = DatatypeParseException.class)
    public void testGetBooleanDatatype_invalid() throws DatatypeParseException {
        Resource dt = XSD.BOOLEAN;
        String lex = "not a boolean";
        DatatypeFactory.getDatatype(lex, dt);
    }

    @Test
    public void testGetIntegerDatatype() throws DatatypeParseException {
        Resource dt = XSD.INTEGER;
        String lex = "123";
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNotNull(datatype);
        assertTrue(datatype instanceof XsdInteger);
    }

    @Test(expected = DatatypeParseException.class)
    public void testGetIntegerDatatype_invalid() throws DatatypeParseException {
        Resource dt = XSD.INTEGER;
        String lex = "abc";
        DatatypeFactory.getDatatype(lex, dt);
    }
    
    @Test
    public void testGetXmlLiteralDatatype() throws DatatypeParseException {
        Resource dt = RDF.XMLLITERAL;
        String lex = "<root><child/></root>";
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNotNull(datatype);
        assertTrue(datatype instanceof RdfXmlLiteral);
    }

    @Test
    public void testGetDatatype_nullLexicalValue() throws DatatypeParseException {
        Resource dt = XSD.STRING;
        String lex = null;
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNull(datatype);
    }

    @Test
    public void testGetDatatype_nullDatatypeURI() throws DatatypeParseException {
        Resource dt = null;
        String lex = "test string";
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNull(datatype);
    }

    @Test
    public void testGetDatatype_unsupportedDatatype() throws DatatypeParseException {
        Resource dt = new Resource("http://example.org/unsupported#Datatype");
        String lex = "some value";
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(lex, dt);
        assertNull(datatype);
    }
    
    @Test
    public void testGetDatatypeFromLiteral_string() throws DatatypeParseException, ParseException {
        Literal l = new Literal("hello", XSD.STRING);
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(l);
        assertNotNull(datatype);
        assertTrue(datatype instanceof XsdString);
    }

    @Test
    public void testGetDatatypeFromLiteral_boolean() throws DatatypeParseException, ParseException {
        Literal l = new Literal("true", XSD.BOOLEAN);
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(l);
        assertNotNull(datatype);
        assertTrue(datatype instanceof XsdBoolean);
    }
    
    @Test(expected = DatatypeParseException.class)
    public void testGetDatatypeFromLiteral_invalidBoolean() throws DatatypeParseException, ParseException {
        Literal l = new Literal("not-a-boolean", XSD.BOOLEAN);
        DatatypeFactory.getDatatype(l);
    }
    
    @Test
    public void testGetDatatypeFromLiteral_plainLiteral() throws DatatypeParseException, ParseException {
        Literal l = new Literal("plain text"); // No datatype, no lang tag
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(l);
        assertNull(datatype);
    }

    @Test
    public void testGetDatatypeFromLiteral_langTaggedLiteral() throws DatatypeParseException, ParseException {
        Literal l = new Literal("hello", "en"); // Lang tagged literal
        Datatype<? extends Object> datatype = DatatypeFactory.getDatatype(l);
        assertNull(datatype);
    }
}
