# -*- coding: utf-8 -*-

"""
    dnslib
    ------

    A simple library to encode/decode DNS wire-format packets. This was
    originally written for a custom nameserver.

    The key classes are:

        * DNSRecord (contains a DNSHeader and one or more DNSQuestion/
                     DNSRR records)
        * DNSHeader 
        * DNSQuestion
        * RR (resource records)
        * RD (resource data - superclass for TXT,A,AAAA,MX,CNAME,PRT,SOA,NAPTR)
        * DNSLabel (envelope for a DNS label)

    The library has (in theory) very rudimentary support for EDNS0 options
    however this has not been tested due to a lack of data (anyone wanting
    to improve support or provide test data please raise an issue)

    Note: In version 0.3 the library was modified to use the DNSLabel class to
    support arbirary DNS labels (as specified in RFC2181) - and specifically
    to allow embedded '.'s. In most cases this is transparent (DNSLabel will
    automatically convert a domain label presented as a dot separated string &
    convert pack to this format when converted to a string) however to get the
    underlying label data (as a tuple) you need to access the DNSLabel.label
    attribute. To specifiy a label to the DNSRecord classes you can either pass
    a DNSLabel object or pass the elements as a list/tuple.

    To decode a DNS packet:

    >>> packet = binascii.unhexlify(b'd5ad818000010005000000000377777706676f6f676c6503636f6d0000010001c00c0005000100000005000803777777016cc010c02c0001000100000005000442f95b68c02c0001000100000005000442f95b63c02c0001000100000005000442f95b67c02c0001000100000005000442f95b93')
    >>> d = DNSRecord.parse(packet)
    >>> d
    <DNS Header: id=0xd5ad type=RESPONSE opcode=QUERY flags=RD,RA rcode='NOERROR' q=1 a=5 ns=0 ar=0>
    <DNS Question: 'www.google.com.' qtype=A qclass=IN>
    <DNS RR: 'www.google.com.' rtype=CNAME rclass=IN ttl=5 rdata='www.l.google.com.'>
    <DNS RR: 'www.l.google.com.' rtype=A rclass=IN ttl=5 rdata='66.249.91.104'>
    <DNS RR: 'www.l.google.com.' rtype=A rclass=IN ttl=5 rdata='66.249.91.99'>
    <DNS RR: 'www.l.google.com.' rtype=A rclass=IN ttl=5 rdata='66.249.91.103'>
    <DNS RR: 'www.l.google.com.' rtype=A rclass=IN ttl=5 rdata='66.249.91.147'>

    The default text representation of the DNSRecord is in zone file format:

    >>> print(d)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 54701
    ;; flags: qr rd ra; QUERY: 1, ANSWER: 5, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;www.google.com.                IN      A
    ;; ANSWER SECTION:
    www.google.com.         5       IN      CNAME   www.l.google.com.
    www.l.google.com.       5       IN      A       66.249.91.104
    www.l.google.com.       5       IN      A       66.249.91.99
    www.l.google.com.       5       IN      A       66.249.91.103
    www.l.google.com.       5       IN      A       66.249.91.147

    To create a DNS Request Packet:

    >>> d = DNSRecord(q=DNSQuestion("google.com"))
    >>> d
    <DNS Header: id=... type=QUERY opcode=QUERY flags=RD rcode='NOERROR' q=1 a=0 ns=0 ar=0>
    <DNS Question: 'google.com.' qtype=A qclass=IN>

    >>> str(DNSRecord.parse(d.pack())) == str(d)
    True

    >>> print(d)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: rd; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;google.com.                    IN      A

    >>> d = DNSRecord(q=DNSQuestion("google.com",QTYPE.MX))
    >>> str(DNSRecord.parse(d.pack())) == str(d)
    True

    >>> print(d)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: rd; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;google.com.                    IN      MX

    To create a DNS Response Packet:

    >>> d = DNSRecord(DNSHeader(qr=1,aa=1,ra=1),
    ...               q=DNSQuestion("abc.com"),
    ...               a=RR("abc.com",rdata=A("1.2.3.4")))
    >>> d
    <DNS Header: id=... type=RESPONSE opcode=QUERY flags=AA,RD,RA rcode='NOERROR' q=1 a=1 ns=0 ar=0>
    <DNS Question: 'abc.com.' qtype=A qclass=IN>
    <DNS RR: 'abc.com.' rtype=A rclass=IN ttl=0 rdata='1.2.3.4'>
    >>> str(DNSRecord.parse(d.pack())) == str(d)
    True

    >>> print(d)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;abc.com.                       IN      A
    ;; ANSWER SECTION:
    abc.com.                0       IN      A       1.2.3.4

    It is also possible to create RRs from a string in zone file format

    >>> RR.fromZone("abc.com IN A 1.2.3.4")
    [<DNS RR: 'abc.com.' rtype=A rclass=IN ttl=0 rdata='1.2.3.4'>]

    The zone file can contain multiple entries and supports most of the normal
    format defined in RFC1035 (specifically not $INCLUDE)

    >>> z = '''
    ...         $TTL 300
    ...         $ORIGIN abc.com
    ...
    ...         @       IN      MX      10  mail.abc.com.
    ...         www     IN      A       1.2.3.4
    ...                 IN      TXT     "Some Text"
    ...         mail    IN      CNAME   www.abc.com.
    ... '''
    >>> for rr in RR.fromZone(textwrap.dedent(z)):
    ...     print(rr)
    abc.com.                300     IN      MX      10 mail.abc.com.
    www.abc.com.            300     IN      A       1.2.3.4
    www.abc.com.            300     IN      TXT     "Some Text"
    mail.abc.com.           300     IN      CNAME   www.abc.com.

    To create a skeleton reply to a DNS query:

    >>> q = DNSRecord(q=DNSQuestion("abc.com",QTYPE.ANY)) 
    >>> a = q.reply()
    >>> a.add_answer(RR("abc.com",QTYPE.A,rdata=A("1.2.3.4"),ttl=60))
    >>> str(DNSRecord.parse(a.pack())) == str(a)
    True
    >>> print(a)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;abc.com.                       IN      ANY
    ;; ANSWER SECTION:
    abc.com.                60      IN      A       1.2.3.4

    Add additional RRs:

    >>> a.add_answer(RR("xxx.abc.com",QTYPE.A,rdata=A("1.2.3.4")))
    >>> a.add_answer(RR("xxx.abc.com",QTYPE.AAAA,rdata=AAAA("1234:5678::1")))
    >>> str(DNSRecord.parse(a.pack())) == str(a)
    True
    >>> print(a)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 3, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;abc.com.                       IN      ANY
    ;; ANSWER SECTION:
    abc.com.                60      IN      A       1.2.3.4
    xxx.abc.com.            0       IN      A       1.2.3.4
    xxx.abc.com.            0       IN      AAAA    1234:5678::1


    It is also possible to create a reply from a string in zone file format:

    >>> q = DNSRecord(q=DNSQuestion("abc.com",QTYPE.ANY)) 
    >>> a = q.replyZone("abc.com 60 IN CNAME xxx.abc.com")
    >>> print(a)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;abc.com.                       IN      ANY
    ;; ANSWER SECTION:
    abc.com.                60      IN      CNAME   xxx.abc.com.

    >>> str(DNSRecord.parse(a.pack())) == str(a)
    True

    >>> q = DNSRecord(q=DNSQuestion("abc.com",QTYPE.ANY)) 
    >>> a = q.replyZone(textwrap.dedent(z))
    >>> print(a)
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: ...
    ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 4, AUTHORITY: 0, ADDITIONAL: 0
    ;; QUESTION SECTION:
    ;abc.com.                       IN      ANY
    ;; ANSWER SECTION:
    abc.com.                300     IN      MX      10 mail.abc.com.
    www.abc.com.            300     IN      A       1.2.3.4
    www.abc.com.            300     IN      TXT     "Some Text"
    mail.abc.com.           300     IN      CNAME   www.abc.com.

    Changelog:

        *   0.1     2010-09-19  Initial Release
        *   0.2     2010-09-22  Minor fixes
        *   0.3     2010-10-02  Add DNSLabel class to support arbitrary labels (embedded '.')
        *   0.4     2012-02-26  Merge with dbslib-circuits
        *   0.5     2012-09-13  Add support for RFC2136 DDNS updates
                                Patch provided by Wesley Shields <wxs@FreeBSD.org> - thanks
        *   0.6     2012-10-20  Basic AAAA support
        *   0.7     2012-10-20  Add initial EDNS0 support (untested)
        *   0.8     2012-11-04  Add support for NAPTR, Authority RR and additional RR
                                Patch provided by Stefan Andersson (https://bitbucket.org/norox) - thanks
        *   0.8.1   2012-11-05  Added NAPTR test case and fixed logic error
                                Patch provided by Stefan Andersson (https://bitbucket.org/norox) - thanks
        *   0.8.2   2012-11-11  Patch to fix IPv6 formatting
                                Patch provided by Torbjörn Lönnemark (https://bitbucket.org/tobbezz) - thanks
        *   0.8.3   2013-04-27  Don't parse rdata if rdlength is 0
                                Patch provided by Wesley Shields <wxs@FreeBSD.org> - thanks

    License:

        *   BSD

    Author:

        *   Paul Chakravarti (paul.chakravarti@gmail.com)

    Master Repository/Issues:

        *   https://bitbucket.org/paulc/dnslib

"""

from dnslib.dns import *
#from dnslib.dns import DNSRecord,DNSHeader,DNSQuestion,RR,CLASS,RDMAP,QR,RCODE

version = "0.9.0"

if __name__ == '__main__':
    import doctest,textwrap
    doctest.testmod(optionflags=doctest.ELLIPSIS)

