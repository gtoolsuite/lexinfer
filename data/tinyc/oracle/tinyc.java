import java.io.*;

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;

public class tinyc {
    public static void main(String[] args) {
        try(FileInputStream fis = new FileInputStream(new File(args[0]))) {
            CharStream in = CharStreams.fromStream(fis);
            TokenSource tokenSource = new tinycLexer(in);
            
            while(true) {
                Token token = tokenSource.nextToken();

                if(token.getType() == Token.EOF) {
                    break;
                }

                System.out.println(token.getText());
            }

        } catch(IOException e) {
            e.printStackTrace();
        } catch(Exception e) {
            e.printStackTrace();
        }
    }
}
