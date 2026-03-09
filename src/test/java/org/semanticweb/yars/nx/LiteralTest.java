package org.semanticweb.yars.nx;

import org.junit.Test;
import static org.junit.Assert.*;

public class LiteralTest {

    @Test
    public void testLiteral_SimpleString() {
        Literal literal = new Literal("hello");
        assertEquals("hello", literal.getLabel());
        assertNull(literal.getLanguageTag());
        assertNull(literal.getDatatype());
        assertEquals(""hello"", literal.toString());
    }

    @Test
    public void testLiteral_EmptyString() {
        Literal literal = new Literal("");
        assertEquals("", literal.getLabel());
        assertNull(literal.getLanguageTag());
        assertNull(literal.getDatatype());
        assertEquals("""", literal.toString());
    }

    @Test
    public void testLiteral_SpecialCharacters() {
        Literal literal = new Literal("hello
world	!");
        assertEquals("hello
world	!", literal.getLabel());
        assertEquals(""hello
world	!"", literal.toString());
    }

    @Test
    public void testLiteral_NTriplesTrue_SimpleString() {
        Literal literal = new Literal(""hello"", true);
        assertEquals("hello", literal.getLabel());
        assertNull(literal.getLanguageTag());
        assertNull(literal.getDatatype());
        assertEquals(""hello"", literal.toString());
    }

    @Test
    public void testLiteral_NTriplesTrue_WithLang() {
        Literal literal = new Literal(""hello"@en", true);
        assertEquals("hello", literal.getLabel());
        assertEquals("en", literal.getLanguageTag());
        assertNull(literal.getDatatype());
        assertEquals(""hello"@en", literal.toString());
    }

    @Test
    public void testLiteral_NTriplesTrue_WithDatatype() {
        Resource datatype = new Resource("http://www.w3.org/2001/XMLSchema#string", true);
        Literal literal = new Literal(""123"^^<http://www.w3.org/2001/XMLSchema#integer>", true);
        assertEquals("123", literal.getLabel());
        assertNull(literal.getLanguageTag());
        assertEquals(new Resource("http://www.w3.org/2001/XMLSchema#integer", true), literal.getDatatype());
        assertEquals(""123"^^<http://www.w3.org/2001/XMLSchema#integer>", literal.toString());
    }

    @Test
    public void testLiteral_NTriplesFalse_SimpleString() {
        Literal literal = new Literal("hello", false);
        assertEquals("hello", literal.getLabel());
        assertNull(literal.getLanguageTag());
        assertNull(literal.getDatatype());
        assertEquals(""hello"", literal.toString());
    }

    @Test
    public void testLiteral_WithLanguage() {
        Literal literal = new Literal("hello", "en");
        assertEquals("hello", literal.getLabel());
        assertEquals("en", literal.getLanguageTag());
        assertNull(literal.getDatatype());
        assertEquals(""hello"@en", literal.toString());
    }

    @Test
    public void testLiteral_WithDatatype() {
        Resource datatype = new Resource("http://www.w3.org/2001/XMLSchema#integer", true);
        Literal literal = new Literal("123", datatype);
        assertEquals("123", literal.getLabel());
        assertNull(literal.getLanguageTag());
        assertEquals(datatype, literal.getDatatype());
        assertEquals(""123"^^<http://www.w3.org/2001/XMLSchema#integer>", literal.toString());
    }

    @Test(expected = IllegalArgumentException.class)
    public void testLiteral_WithLanguageAndDatatype_ThrowsException() {
        Resource datatype = new Resource("http://www.w3.org/2001/XMLSchema#string", true);
        new Literal("hello", "en", datatype);
    }

    @Test
    public void testLiteral_GetLabel() {
        Literal literal1 = new Literal("test label");
        assertEquals("test label", literal1.getLabel());

        Literal literal2 = new Literal(""escaped
label"@en", true);
        assertEquals("escaped
label", literal2.getLabel());
    }

    @Test
    public void testLiteral_GetLanguageTag() {
        Literal literal1 = new Literal("hello", "fr");
        assertEquals("fr", literal1.getLanguageTag());

        Literal literal2 = new Literal("hello");
        assertNull(literal2.getLanguageTag());

        Resource datatype = new Resource("http://www.w3.org/2001/XMLSchema#integer", true);
        Literal literal3 = new Literal("123", datatype);
        assertNull(literal3.getLanguageTag());
    }

    @Test
    public void testLiteral_GetDatatype() {
        Resource datatype = new Resource("http://www.w3.org/2001/XMLSchema#boolean", true);
        Literal literal1 = new Literal("true", datatype);
        assertEquals(datatype, literal1.getDatatype());

        Literal literal2 = new Literal("hello");
        assertNull(literal2.getDatatype());

        Literal literal3 = new Literal("hello", "es");
        assertNull(literal3.getDatatype());
    }

    @Test
    public void testLiteral_ToString() {
        Literal literal1 = new Literal("value");
        assertEquals(""value"", literal1.toString());

        Literal literal2 = new Literal("another value", "de");
        assertEquals(""another value"@de", literal2.toString());

        Resource datatype = new Resource("http://example.org/datatype", true);
        Literal literal3 = new Literal("1.0", datatype);
        assertEquals(""1.0"^^<http://example.org/datatype>", literal3.toString());
    }

    @Test
    public void testLiteral_EqualsAndHashCode() {
        Literal literal1 = new Literal("test");
        Literal literal2 = new Literal("test");
        Literal literal3 = new Literal("other");

        assertTrue(literal1.equals(literal2));
        assertFalse(literal1.equals(literal3));
        assertFalse(literal1.equals(null));
        assertFalse(literal1.equals(new Object()));

        assertEquals(literal1.hashCode(), literal2.hashCode());
        assertFalse(literal1.hashCode() == literal3.hashCode());
    }

    @Test
    public void testLiteral_CompareTo() {
        Literal literal1 = new Literal("apple");
        Literal literal2 = new Literal("banana");
        Literal literal3 = new Literal("apple");

        assertTrue(literal1.compareTo(literal2) < 0);
        assertTrue(literal2.compareTo(literal1) > 0);
        assertTrue(literal1.compareTo(literal3) == 0);
    }

    @Test
    public void testLiteral_NtriplesString() {
        Literal literal = new Literal("example");
        assertEquals(""example"", literal.ntriplesString());

        Literal literalWithLang = new Literal("text", "en");
        assertEquals(""text"@en", literalWithLang.ntriplesString());
    }

    @Test
    public void testLiteral_GetLexicalForm() {
        Literal literal = new Literal("lexical form test");
        assertEquals("lexical form test", literal.getLexicalForm());

        Literal literalWithEscape = new Literal("escape
char");
        assertEquals("escape
char", literalWithEscape.getLexicalForm());
    }
}
